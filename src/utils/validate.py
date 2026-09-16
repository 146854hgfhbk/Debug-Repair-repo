from config import BasicConfig, LLMConfig, ValidatorConfig
import os
import signal
import subprocess
import time
from defs.bug_info import BugInfo

from typing import Tuple

PLATFORM = BasicConfig.PLATFORM
PROCESS_GROUP_GRACE_SECONDS = 2.0
PROCESS_KILL_SIGNAL = getattr(signal, "SIGKILL", 9)


def _process_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _terminate_process_group(child, grace_seconds=PROCESS_GROUP_GRACE_SECONDS):
    if PLATFORM != "linux" or not hasattr(os, "killpg"):
        if child.poll() is not None:
            child.wait()
            return
        child.terminate()
        try:
            child.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
        return

    # start_new_session=True makes the launched process the group leader, so
    # its PID remains the PGID even if that leader exits before its children.
    process_group_id = child.pid
    if child.poll() is not None and not _process_group_exists(process_group_id):
        child.wait()
        return

    try:
        os.killpg(process_group_id, signal.SIGTERM)
    except ProcessLookupError:
        child.wait()
        return

    deadline = time.monotonic() + max(0, grace_seconds)
    group_alive = _process_group_exists(process_group_id)
    while group_alive:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            child.wait(timeout=min(0.1, remaining))
        except subprocess.TimeoutExpired:
            pass
        group_alive = _process_group_exists(process_group_id)

    if group_alive:
        try:
            os.killpg(process_group_id, PROCESS_KILL_SIGNAL)
        except ProcessLookupError:
            pass

    try:
        child.wait(timeout=max(1.0, grace_seconds))
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


def _run_defects4j(args, cwd=None):
    command = [ValidatorConfig.DEFECTS4J_EXECUTABLE, *args]
    child = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env=os.environ.copy(),
    )
    try:
        stdout, stderr = child.communicate(
            timeout=ValidatorConfig.FULL_TEST_TIMEOUT_LIMIT
        )
    except subprocess.TimeoutExpired:
        _terminate_process_group(child)
        raise
    return subprocess.CompletedProcess(
        command,
        child.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _stderr_path(temp_path: str) -> str:
    return os.path.join(temp_path, "stderr.txt")


def _read_source_lines(path: str):
    try:
        with open(path, "r", encoding="utf-8") as source_file:
            return source_file.read().split("\n")
    except UnicodeDecodeError:
        with open(path, "r", encoding="ISO-8859-1") as source_file:
            return source_file.read().split("\n")

def validate_patch(
    bug_id: str,
    patch: str,
    bug_info: BugInfo
) -> Tuple[bool, str]:
    """
    验证补丁是否通过测试
    """
    # Check for remote delegation
    try:
        from utils import remote_validation
        if remote_validation.is_remote_validation_enabled():
            result = remote_validation.request_remote_validation(
                "validate_patch", bug_id, patch
            )
            return tuple(result)
    except ImportError:
        pass
    except remote_validation.RemoteValidationError:
        raise

    # 获取bug的项目和编号
    project = bug_id.split('-')[0]
    id = bug_id.split('-')[1]

    temp_path = os.path.join(BasicConfig.TEMP_PATH, BasicConfig.MODE, LLMConfig.LLM_MODEL, "test_"+bug_id)
    print(temp_path)
    _delete_dir(temp_path)

    checkout = _run_defects4j(
        ["checkout", "-p", project, "-v", f"{id}b", "-w", temp_path]
    )
    if checkout.returncode != 0:
        return False, "Checkout Fail: " + (checkout.stderr or checkout.stdout).strip()
    trigger_export = _run_defects4j(
        ["export", "-w", temp_path, "-p", "tests.trigger"]
    )
    if trigger_export.returncode != 0:
        return False, "Trigger Export Fail: " + (trigger_export.stderr or trigger_export.stdout).strip()
    testmethods = trigger_export.stdout.splitlines()

    #获取src目录
    try:
        source_export = _run_defects4j(
            ["export", "-p", "dir.src.classes", "-w", temp_path]
        )
        source_dir = [line for line in source_export.stdout.splitlines() if line.strip()][-1].strip()
    except IndexError:
        print(f"无法获取源代码目录: {temp_path}")
        source_dir = ""

    
    with open(f"{BasicConfig.LOC_PATH}/{bug_id}.buggy.lines", "r") as f:
        locs = f.read()

    loc = set([x.split("#")[0] for x in locs.splitlines() if x.strip()])  # 过滤空行, 并截断#后面的内容

    if not loc:
        print(f"无法从 .buggy.lines 文件中找到源文件路径 (Bug ID: {bug_id})")
        _delete_dir(temp_path)
        return False, "无法从 .buggy.lines 文件中找到源文件路径"
    
    loc = loc.pop()
    
    source_path = f"{temp_path}/{source_dir}/{loc}"
    source = _read_source_lines(source_path)
    
    # 向源码插入补丁
    patch_lines = patch.splitlines()
    source = "\n".join(source[:bug_info.start_line - 1] + patch_lines + source[bug_info.end_line:])

    # 调试模式则导出预览文件
    if BasicConfig.DEBUG_MODE:
        debug_filename = f"debug_patched_{bug_id}.java"
        print(f"\n[DEBUG] 正在将应用补丁后的代码导出到: {os.path.abspath(debug_filename)}")
        try:
            if os.path.exists(BasicConfig.DEBUG_PATH) == False:
                os.mkdir(BasicConfig.DEBUG_PATH)
            with open(f"{BasicConfig.DEBUG_PATH}/{debug_filename}", "w", encoding='utf-8') as debug_f:
                debug_f.write(source)
            print(f"[DEBUG] 导出成功")
        except Exception as e:
            print(f"[DEBUG] 导出失败: {e}")
    
    # 写入插入补丁后的程序
    try:
        with open(f"{temp_path}/{source_dir}/{loc}", 'w') as f:
            f.write(source)
    except:
        with open(f"{temp_path}/{source_dir}/{loc}", 'w', encoding='ISO-8859-1') as f:
            f.write(source)

    # 运行测试
    compile_fail, timed_out, buggy, syntax_error, log = _run_test(source, testmethods, temp_path)

    _delete_dir(temp_path)

    if not compile_fail and not timed_out and not buggy and not syntax_error:
        print("{} has valid patch".format(bug_id))
        return True, ""
    else:
        print("{} has invalid patch".format(bug_id))
        if compile_fail: message = "Compile Fail"
        elif timed_out: message = "Time Out"
        elif syntax_error: message = "Syntex Error"
        else: message = "Failing test: " + log[-1].decode('utf-8')[4:-1]
        return False, message

import javalang

def _run_test(source, testmethods, temp_path):
    buggy = False
    compile_fail = False
    timed_out = False
    env = os.environ.copy()
    env['LC_ALL'] = 'en_US.UTF-8'
    env['LANG'] = 'en_US.UTF-8'
    # 语法检查
    try:
        tokens = javalang.tokenizer.tokenize(source)
        parser = javalang.parser.Parser(tokens)
        parser.parse()
    except:
        print("Syntax Error")
        return compile_fail, timed_out, buggy, True, None

    # 运行触发测试
    for t in testmethods:
        print(t.strip())
        cmd = [
            ValidatorConfig.DEFECTS4J_EXECUTABLE,
            "test",
            "-w",
            f"{temp_path}/",
            "-t",
            t.strip(),
        ]
        Returncode = ""
        error_file = open(_stderr_path(temp_path), "wb")

        child = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=error_file, 
            bufsize=-1,
            start_new_session=True,
            env=env
        )

        while_begin = time.time()
        while True:
            Flag = child.poll()
            # 1. 正常结束
            if Flag == 0:
                Returncode = child.stdout.readlines()
                print(b"".join(Returncode).decode('utf-8'))
                error_file.close()
                break
            # 2. 报错结束 (Regression Test Failed 或 编译失败)
            elif Flag != 0 and Flag is not None:
                compile_fail = True
                error_file.close()
                buggy = True
                break
            # 3. 超时检测
            elif time.time() - while_begin > ValidatorConfig.TRIGGER_TEST_TIMEOUT_LIMIT:
                _terminate_process_group(child)
                error_file.close()
                # os.killpg(os.getpgid(child.pid), signal.SIGTERM) # TODO : 这个写法可能有问题
                print(f"检测到触发测试超时 (>{ValidatorConfig.TRIGGER_TEST_TIMEOUT_LIMIT}s)")
                timed_out = True
                buggy = True
                break
            else:
                time.sleep(1)

        log = Returncode
        if len(log) > 0 and log[-1].decode('utf-8') == "Failing tests: 0\n":
            print('success in trigger test\n')
        else:
            print('failed in trigger test\n')
            buggy = True
            break

    # 运行全量测试
    if not buggy:
        print('通过触发测试, 运行全量测试')
        cmd = [
            ValidatorConfig.DEFECTS4J_EXECUTABLE,
            "test",
            "-w",
            f"{temp_path}/",
        ]
        Returncode = ""
        timed_out = False 
            
        child = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            bufsize=-1,
            start_new_session=True,
            env=env
        )
        
        while_begin = time.time()

        while True:
            Flag = child.poll()
            
            # 1. 正常结束
            if Flag == 0:
                Returncode = child.stdout.readlines()
                break
            # 2. 报错结束 (Regression Test Failed 或 编译失败)
            elif Flag != 0 and Flag is not None:
                buggy = True
                compile_fail = True
                break
            # 3. 超时检测
            elif time.time() - while_begin > ValidatorConfig.FULL_TEST_TIMEOUT_LIMIT:
                _terminate_process_group(child)
                # os.killpg(os.getpgid(child.pid), signal.SIGTERM) # TODO : 这个写法可能有问题
                print(f"检测到全量测试超时 (>{ValidatorConfig.FULL_TEST_TIMEOUT_LIMIT}s)")
                timed_out = True
                buggy = True
                break
            else:
                time.sleep(1)

        log = Returncode
        if len(log) > 0 and log[-1].decode('utf-8') == "Failing tests: 0\n":
            print('success in all test')
        else:
            print('failed in all test')
            buggy = True

    return compile_fail, timed_out, buggy, False, log


def _delete_dir(path: str):
    """删除目录"""
    if not path or not os.path.exists(path):
        return
    if BasicConfig.PLATFORM == "windows":
        subprocess.run(f"rd /s /q {path}", shell=True)
    elif BasicConfig.PLATFORM == "linux":
        subprocess.run(f"rm -rf {path}", shell=True)
