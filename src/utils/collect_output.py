from defs.bug_info import BugInfo
from config import BasicConfig, LLMConfig, ValidatorConfig
import subprocess
import os

from utils.timeout_utils import timeout

from typing import Optional

@timeout(ValidatorConfig.COLLECT_OUTPUT_TIMEOUT_LIMIT)
def collect_output(
        bug_id: str,
        bug_info: BugInfo,
        instrumented_method: str,
    ) -> str:
    # 获取bug的项目和编号
    project = bug_id.split('-')[0]
    id = bug_id.split('-')[1]

    test_class, test_function_name = _get_test_info(project, id)

    temp_path = os.path.join(BasicConfig.TEMP_PATH, BasicConfig.MODE, LLMConfig.LLM_MODEL, "test_"+bug_id)
    print(temp_path)

    _delete_dir(temp_path)

    subprocess.run(f"defects4j checkout -p {project} -v {id}b -w {temp_path}", shell=True)
    testmethods = os.popen(f"defects4j export -w {temp_path} -p tests.trigger").readlines()


    # -----------------------------------------------------
    # 获取测试目录
    test_dir = os.popen(f"defects4j export -p dir.src.tests -w {temp_path}").readlines()[-1].strip()
    
    # 获取测试文件路径
    test_location = test_class.replace('.', '/') + '.java'
    test_file_path = f"{temp_path}/{test_dir}/{test_location}"

    # 加载并替换测试函数
    test_function_code = _load_test_function_code(bug_info)
    if test_function_code:
        # 替换测试函数
        success = _replace_test_function(test_file_path, test_function_name, test_function_code)
        if not success:
            print(f"[WARNING] 替换测试函数失败，将使用原测试函数")
            # 如果替换失败，至少在原函数中添加调试输出
            _add_print_to_function(test_file_path, test_function_name, buggy_code=False)
    else:
        # 没有新的测试函数代码，只在原函数中添加调试输出
        _add_print_to_function(test_file_path, test_function_name, buggy_code=False)
    # -----------------------------------------------------
    

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
    patch_lines = instrumented_method.splitlines()
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

    success, output = _run_and_collect_output(source, testmethods, test_class, temp_path)
    _delete_dir(temp_path)
    return output

def _run_and_collect_output(source, testmethods, test_class, temp_path):
    env = os.environ.copy()
    
    # 1. 首先导出 classpath
    print("[DEBUG] STEP 1: START - defects4j export")
    cp_result = subprocess.run(
        "defects4j export -p cp.test -o cp_test.txt",
        cwd=temp_path,
        capture_output=True,
        text=True,
        shell=True,
        check=True,
        env=env
    )
    print(f"[DEBUG] STEP 1: SUCCESS - defects4j export")
    
    # 2. 编译
    print("[DEBUG] STEP 2: START - defects4j compile")
    compile_result = subprocess.run(
        "defects4j compile",
        cwd=temp_path,
        capture_output=True,
        text=True,
        shell=True,
        check=False,  # 改为 check=False 以便查看错误
        env=env
    )
    if compile_result.returncode != 0:
        print(f"[DEBUG] 编译失败，返回码: {compile_result.returncode}")
        print(f"[DEBUG] 编译输出: {compile_result.stdout}")
        print(f"[DEBUG] 编译错误: {compile_result.stderr}")
        return False, f"编译失败: {compile_result.stderr}"
    else:
        print("[DEBUG] STEP 2: SUCCESS - defects4j compile")
    
    # 3. 检查测试类文件是否存在
    print(f"[DEBUG] STEP 3: 检查测试类 {test_class}")
    
    # 获取测试目录
    test_dir_result = subprocess.run(
        "defects4j export -p dir.src.tests",
        cwd=temp_path,
        capture_output=True,
        text=True,
        shell=True,
        env=env
    )
    test_dir = test_dir_result.stdout.strip()
    print(f"[DEBUG] 测试目录: {test_dir}")
    
    # 将包名转换为路径
    test_class_path = test_class.replace('.', '/') + '.java'
    test_file_path = f"{temp_path}/{test_dir}/{test_class_path}"
    print(f"[DEBUG] 预期测试文件路径: {test_file_path}")
    print(f"[DEBUG] 文件是否存在: {os.path.exists(test_file_path)}")
    
    # 4. 运行测试
    print("[DEBUG] STEP 4: START - java run test")
    print(f"[DEBUG] 尝试使用 JUnitCore 运行 {test_class}")
    run_re = subprocess.run(
        f"java -cp $(cat cp_test.txt) org.junit.runner.JUnitCore {test_class} > test_output.txt 2>&1",
        capture_output=True,
        text=True,
        timeout=30,
        cwd=temp_path,
        shell=True,
        env=env
    )
    
    # 5. 读取输出
    output_path = f"{temp_path}/test_output.txt"
    if os.path.exists(output_path):
        with open(output_path, 'r') as f:
            output = _extract_debug_info(f.read())

    return run_re.returncode == 0, output

def _get_test_info(project, id):
    with open(f"{BasicConfig.D4J_PATH}/framework/projects/{project}/trigger_tests/{id}",'r') as f:
        test_location=f.readline()

    test_location=test_location.split(' ')[1]
    test_function_name=test_location.split("::")[1].strip()
    test_class=test_location.split("::")[0].strip()

    return test_class,test_function_name

def _load_test_function_code(bug_info: BugInfo) -> Optional[str]:
    candidate_path = os.path.join(BasicConfig.TEST_PATH, f"{bug_info.bug_id}.java")
    if os.path.exists(candidate_path):
        with open(candidate_path, "r", encoding="utf-8") as f:
            content = f.read()
        if content.strip():
            return content

    # for test in bug_info.trigger_test or []:
    #     for key in ("failing_function", "sliced_test"):
    #         snippet = test.get(key)
    #         if isinstance(snippet, str) and snippet.strip():
    #             return snippet.strip()
    return None


def _delete_dir(path: str):
    """删除目录"""
    print(f"[DEBUG] 删除目录: {path}")

    if not path or not os.path.exists(path):
        return
    if BasicConfig.PLATFORM == "windows":
        subprocess.run(f"rd /s /q {path}", shell=True)
    elif BasicConfig.PLATFORM == "linux":
        subprocess.run(f"rm -rf {path}", shell=True)


# 以下代码不知道是否合理
# 在 _run_and_collect_output 函数之前添加这些函数

def _add_print_to_function(file_path, function_name, added_code=None, buggy_code=False):
    """向指定函数添加调试输出，如果是buggy_code则替换整个函数"""
    try:
        with open(file_path, 'r', encoding='ISO-8859-1') as f:
            java_code_lines = f.readlines()
        
        indexes = []
        if not buggy_code:
            # 对于测试函数，查找 " function_name("
            search_pattern = ' ' + function_name + '('
        else:
            # 对于buggy函数，直接查找函数名
            search_pattern = function_name
        
        for index, line in enumerate(java_code_lines):
            if (search_pattern in line) and java_code_lines[index].strip()[0] != '/' and java_code_lines[index].strip()[0] != '*':
                indexes.append(index)
        
        if len(indexes) != 1:
            print(f"[WARNING] 在文件 {file_path} 中未找到函数 {function_name} 或找到多个匹配")
            return False
        
        left_num = 1
        nl = False
        if java_code_lines[indexes[0]].strip()[-1] != '{':
            nl = True
        
        current_line = indexes[0] + 1
        while left_num > 0 and current_line < len(java_code_lines):
            for char in java_code_lines[current_line].strip():
                if char == '}':
                    left_num -= 1
                if char == '{':
                    if nl:
                        nl = False
                    else:
                        left_num += 1
            current_line += 1
        
        if indexes[0] < 0 or java_code_lines[current_line-1].strip()[-1] != "}":
            return False
        
        # 如果是buggy代码，用added_code替换整个函数
        if buggy_code and added_code:
            added_lines1 = added_code.split('\n')
            added_lines = [line + '\n' for line in added_lines1]
            java_code_lines[indexes[0]:current_line] = added_lines
        
        # 如果不是buggy代码，添加调试输出
        if not buggy_code:
            sprint = 'System.out.println("\\nNow runtime output for trigger test begin:\\n");'
            
            # 添加测试函数开始标记
            change_true = False
            super_ex = False
            
            for i in range(indexes[0], current_line):
                if 'super(' in java_code_lines[i] or 'this(' in java_code_lines[i]:
                    super_ex = True
                    for it in range(len(java_code_lines[i])):
                        if java_code_lines[i][it] == ';':
                            java_code_lines[i] = java_code_lines[i][:it + 1] + sprint + java_code_lines[i][it + 1:]
                            change_true = True
                            break
                    break
            
            if not super_ex:
                for i in range(indexes[0], current_line):
                    for it in range(len(java_code_lines[i])):
                        if java_code_lines[i][it] == '{':
                            java_code_lines[i] = java_code_lines[i][:it + 1] + sprint + java_code_lines[i][it + 1:]
                            change_true = True
                            break
                    if change_true:
                        break
        
        with open(file_path, 'w', encoding='ISO-8859-1') as f:
            f.write(''.join(java_code_lines))
        
        return True
    except Exception as e:
        print(f"[ERROR] 添加调试输出到函数失败: {e}")
        return False

def _replace_test_function(test_file_path, test_function_name, new_test_code):
    """替换测试文件中的测试函数"""
    try:
        # 首先在new_test_code中添加调试输出
        debug_line = 'System.out.println("\\nNow runtime output for trigger test begin:\\n");'
        lines = new_test_code.split('\n')
        
        # 找到函数体的开始位置
        for i, line in enumerate(lines):
            if '{' in line:
                # 在{后面添加调试输出
                brace_pos = line.find('{')
                lines[i] = line[:brace_pos+1] + debug_line + line[brace_pos+1:]
                break
        
        modified_test_code = '\n'.join(lines)
        
        # 使用_add_print_to_function替换整个测试函数
        return _add_print_to_function(test_file_path, test_function_name, modified_test_code, buggy_code=True)
    except Exception as e:
        print(f"[ERROR] 替换测试函数失败: {e}")
        return False
    
def _extract_debug_info(output: str) -> str:
    """从测试输出中提取调试信息（与原代码逻辑一致）"""
    lines = output.split('\n')
    
    # 查找调试标记的开始位置
    trigger_start = None
    for i, line in enumerate(lines):
        if "Now runtime output for trigger test begin:" in line:
            trigger_start = i
            break
    
    if trigger_start is None:
        return ""
    
    # 从trigger_start开始，查找以"========Test Case"开头的行
    test_case_start = None
    for i in range(trigger_start, len(lines)):
        if lines[i].strip().startswith("========Test Case"):
            test_case_start = i
            break
    
    if test_case_start is None:
        # 如果没找到"========Test Case"，从trigger_start开始到结束
        test_case_start = trigger_start
    
    # 查找错误信息的开始位置（以"at "开头的行）
    error_start = None
    for i in range(test_case_start, len(lines)):
        if lines[i].strip().startswith("at "):
            error_start = i
            break
    
    if error_start is not None:
        # 如果有错误信息，提取到错误信息之前
        result_lines = lines[test_case_start:error_start]
    else:
        # 如果没有错误信息，提取到结束
        result_lines = lines[test_case_start:]
    
    return '\n'.join(result_lines)