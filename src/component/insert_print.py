from llm.llm_client import LLMClient
from llm.prompt_builder import PromptBuilder
from config import BasicConfig, LLMConfig, HyperParamConfig, ValidatorConfig
from defs.bug_info import BugInfo
from utils.collect_output import collect_output
from utils.extract_code import extract_code_block
from utils.rule_based_insert_print import rule_insert_print
from utils.output_logger import output_log
import re

def insert_print_pipeline(
    bug_id: str,
    bug_info: BugInfo,
    llm_client: LLMClient,
    prompt_builder: PromptBuilder
):
    start_marker = f"// DEBUG_MARKER_START"
    end_marker = f"// DEBUG_MARKER_END"

    flag = False # 记录 llm 是否生成可信插桩
    inserted_code = ""

    for attempt in range(HyperParamConfig.INSERT_MAX_ATTEMPT):
        print(f"尝试插入输出: 第{attempt + 1}/{HyperParamConfig.INSERT_MAX_ATTEMPT}次")

        inserted_code, usage_info = _llm_insert_print(bug_info, llm_client, prompt_builder, start_marker, end_marker)
        output_log(bug_id, "insert_print", inserted_code, "", usage_info)

        if _check_insert_print(bug_info, inserted_code):
            flag = True
            break

    if not flag:
        inserted_code = rule_insert_print(bug_info, start_marker, end_marker)

    instrumented_code = _add_buggy_line_comments(bug_info, inserted_code)
    print("-> 插桩完成")
    print(f"-> 插桩代码: \n{instrumented_code}")

    try:
        output = collect_output(bug_id, bug_info, instrumented_code)
    except Exception as e:
        print(f"  [ERROR] 收集输出失败: {e}")
        output = ""
    
    output_log(bug_id, "insert_print", instrumented_code, output)

    return instrumented_code, output


def _llm_insert_print(
    bug_info: BugInfo,
    llm_client: LLMClient,
    prompt_builder: PromptBuilder,
    start_marker: str,
    end_marker: str
):
    prompt = prompt_builder.build_insert_print_prompt(bug_info.buggy_method, bug_info.sliced_trigger_test, bug_info.error_log, start_marker, end_marker)
    response, usage = llm_client.generate_response(prompt, "insert_print")

    code_block = extract_code_block(response)
    return code_block, usage

import multiprocessing
import time

def _check_insert_print(
    bug_info: BugInfo,
    inserted_code: str
) -> bool:
    original_code = bug_info.buggy_method

    if not original_code or not inserted_code:
        print("[DEBUG] FAILED: 输入代码为空。")
        return False
    
    result_queue = multiprocessing.Queue()
    
    # 创建子进程
    p = multiprocessing.Process(
        target=_check_insert_print_subfunc, 
        args=(original_code, inserted_code, result_queue)
    )
    
    start_time = time.time()
    p.start()
    
    # 等待子进程，超时设置为 10 秒
    p.join(timeout=10)
    
    is_match = False
    
    if p.is_alive():
        print(f"  [TIMEOUT] 验证超时！耗时超过 10 秒。")
        print("  -> 正在强制杀死子进程 (Terminate)...")
        p.terminate() # 强制杀死进程，这是 Thread 做不到的
        p.join()      # 等待进程资源回收
        print("  -> 子进程已终止。判定为验证失败。")
        is_match = False
    else:
        # 进程在限定时间内结束了，获取结果
        if not result_queue.empty():
            is_match = result_queue.get()
            elapsed = time.time() - start_time
            if is_match:
                print(f"[DEBUG] 自检通过 (耗时: {elapsed:.4f}s)")
            else:
                print(f"[DEBUG] 自检不匹配 (耗时: {elapsed:.4f}s)")
        else:
            print("[ERROR] 子进程异常退出，未返回结果。")
            is_match = False
    return is_match

def _add_buggy_line_comments(
    bug_info: BugInfo,
    inserted_code: str
) -> str:
    """基于代码行的内容来为其添加 // Buggy Line 注释"""
    buggy_line_contents = bug_info.buggy_line_contents
    if not inserted_code or not buggy_line_contents:
        return inserted_code
    
    lines = inserted_code.split("\n")
    # 为了避免重复标记，记录已经添加过注释的行索引
    annotated_indices = set()

    for content_to_find in buggy_line_contents:
        # 寻找与 buggy 行内容完全匹配（去除首尾空白后）的行
        for i, line in enumerate(lines):
            if i in annotated_indices:
                continue
            
            # 使用 .strip() 来忽略缩进差异
            if line.strip() == content_to_find:
                if "// Buggy Line" not in lines[i]:
                    lines[i] += " // Buggy Line"
                annotated_indices.add(i)
                break 
                
    return "\n".join(lines)

def _check_insert_print_subfunc(
    original_code: str, 
    instrumented_code: str, 
    result_queue: multiprocessing.Queue
):
    """
    [子进程工作函数] 执行具体的正则验证逻辑。
    将结果放入 Queue 中传回主进程。
    """
    try:
        # 正则表达式：匹配 System.out.println(...)
        # 注意：处理巨型字符串时，这个正则极易导致 CPU 飙升
        println_pattern = re.compile(r'System\.out\.println\s*\((?:[^)(]+|\((?:[^)(]+|\([^)(]*\))*\))*\);', re.DOTALL)
        
        # 步骤 1: 清理打印语句
        cleaned_original = println_pattern.sub('', original_code)
        cleaned_instrumented = println_pattern.sub('', instrumented_code)

        # 步骤 2: 规范化（移除所有空白）
        normalized_original = "".join(cleaned_original.split())
        normalized_instrumented = "".join(cleaned_instrumented.split())
        
        # 步骤 3: 最终对比
        is_match = normalized_original == normalized_instrumented
        
        # 将结果放入队列
        result_queue.put(is_match)
        
    except Exception as e:
        result_queue.put(False)