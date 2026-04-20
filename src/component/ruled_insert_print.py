from config import BasicConfig, LLMConfig, HyperParamConfig, ValidatorConfig
from defs.bug_info import BugInfo
from utils.collect_output import collect_output
from utils.rule_based_insert_print import rule_insert_print
from utils.output_logger import output_log, update_status_and_final_msg

def ruled_insert_print_pipeline(
    bug_id: str,
    bug_info: BugInfo,
):
    start_marker = f"// START_DEBUG"
    end_marker = f"// END_DEBUG"

    inserted_code = ""

    inserted_code = rule_insert_print(bug_info, start_marker, end_marker)

    instrumented_code = _add_buggy_line_comments(bug_info, inserted_code)
    print("-> 插桩完成")
    print(f"-> 插桩代码: \n{instrumented_code}")

    flag = True
    output = ""
    try:
        output = collect_output(bug_id, bug_info, instrumented_code)
    except Exception as e:
        print(f"  [ERROR] 收集输出失败: {e}")
        flag = False

    output_log(bug_id, "ruled_insert_print", instrumented_code, output)
    update_status_and_final_msg(bug_id, flag, "")
    return instrumented_code, output

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
