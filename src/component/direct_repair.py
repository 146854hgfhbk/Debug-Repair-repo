from defs.bug_info import BugInfo
from llm.llm_client import LLMClient
from llm.prompt_builder import PromptBuilder
from typing import Optional, List

from utils.output_logger import output_log
from utils.extract_code import extract_code_block
from utils.validate import validate_patch
from typing import Tuple
def direct_repair_pipeline(
    bug_id: str,
    bug_info: BugInfo,
    llm_client: LLMClient,
    prompt_builder: PromptBuilder
) -> Tuple[bool, str, str, dict]:
    """
    直接修复管线

    Args:
        bug_id, bug_info, llm_client, prompt_builder

    Returns:
        is_ok, msg, code_block, usage
    """

    print("="*50)
    print("Direct Repair 开始")
    code_block, usage = _llm_direct_repair(bug_info, llm_client, prompt_builder)

    if code_block is None:
        print("Direct Repair 失败, 代码块为空")
        output_log(bug_id, "direct_repair", code_block, "Failed -- llm no response or extract code block failed", usage)
        return False, "Failed -- llm no response or extract code block failed", "", usage
    
    is_ok, msg = validate_patch(bug_id, code_block, bug_info)
    output_log(bug_id, "direct_repair", code_block, ("Success" if is_ok else "Failed -- ") + msg, usage)
    print("="*50)
    return is_ok, msg, code_block, usage

def _llm_direct_repair(
    bug_info: BugInfo,
    llm_client: LLMClient,
    prompt_builder: PromptBuilder
) -> Tuple[str, dict]:
    prompt = prompt_builder.build_direct_repair_prompt(bug_info.buggy_method, bug_info.sliced_trigger_test, bug_info.error_log)
    response, usage = llm_client.generate_response(prompt, "direct_repair")

    code_block = extract_code_block(response)
    print(f"Direct Repair 接收llm回应: {response}")
    return code_block, usage
