from defs.bug_info import BugInfo
from utils.collect_output import collect_output
from utils.output_logger import output_log

def run_and_collect_output_pipeline(
    bug_id: str,
    bug_info: BugInfo,
    instrumented_code: str
):
    try:
        output = collect_output(bug_id, bug_info, instrumented_code)
    except Exception as e:
        print(f"  [ERROR] 收集输出失败: {e}")
        output = ""

    output_log(bug_id, "insert_print", instrumented_code, output)

    return output