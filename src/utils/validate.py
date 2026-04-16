from config import BasicConfig, LLMConfig, ValidatorConfig
import os
import subprocess
from defs.bug_info import BugInfo

from typing import Tuple

PLATFORM = BasicConfig.PLATFORM

def validate_patch(
    bug_id: str,
    patch: str,
    bug_info: BugInfo
) -> Tuple[bool, str]:
    """
    验证补丁是否通过测试
    """

    # 获取bug的项目和编号
    project = bug_id.split('-')[0]
    id = bug_id.split('-')[1]

    temp_path = os.path.join(BasicConfig.TEMP_PATH, BasicConfig.MODE, LLMConfig.LLM_MODEL, "test_"+bug_id)
    print(temp_path)
    _delete_dir(temp_path)

    subprocess.run(f"defects4j checkout -p {project} -v {id}b -w {temp_path}", shell=True)
    testmethods = os.popen(f"defects4j export -w {temp_path} -p tests.trigger").readlines()

    #获取src目录
    try:
        source_dir = os.popen(f"defects4j export -p dir.src.classes -w {temp_path}").readlines()[-1].strip()
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
    
    try:
        with open(f"{temp_path}/{source_dir}/{loc}", 'r') as f:
            source = f.read().split('\n')
    except:
        with open(f"{temp_path}/{source_dir}/{loc}" 'r', encoding='ISO-8859-1') as f:
            source = f.read().split('\n')
    
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
import time
import signal

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
        cmd = f"defects4j test -w {temp_path}/ -t {t.strip()}"
        Returncode = ""
        error_file = open("stderr.txt", "wb")

        child = subprocess.Popen(
            cmd, 
            shell=True, 
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
                child.kill()
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
        cmd = f"defects4j test -w {temp_path}/"
        Returncode = ""
        timed_out = False 
            
        child = subprocess.Popen(
            cmd, 
            shell=True, 
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
                child.kill()
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