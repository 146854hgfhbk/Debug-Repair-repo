from defs.bug_info import BugInfo
from llm.llm_client import LLMClient
from llm.prompt_builder import PromptBuilder

from utils.extract_code import extract_code_block
from utils.validate import validate_patch
from utils.output_logger import output_log
from typing import Tuple, List, Optional

def patch_augment_pipeline(
    bug_id: str,
    bug_info: BugInfo,
    llm_client: LLMClient,
    prompt_builder: PromptBuilder,
    plausible_patch: str
) -> Tuple[bool, str, str, dict]:
    """
    补丁增强管线

    Args:
        bug_id, bug_info, llm_client, prompt_builder, plausible_patch

    Returns:
        is_ok, msg, code_block, usage
    """

    print("="*50)
    print("Patch Augment 开始")
    code_block, usage = _llm_augment_patch(bug_info, llm_client, prompt_builder, plausible_patch)

    if code_block is None:
        print("Direct Repair 失败, 代码块为空")
        output_log(bug_id, "patch_augment", code_block, "Failed -- llm no response or extract code block failed", usage)
        return False, "Failed -- llm no response or extract code block failed", "", usage
    
    is_ok, msg = validate_patch(bug_id, code_block, bug_info)
    output_log(bug_id, "patch_augment", code_block, ("Plausible" if is_ok else "Failed -- ") + msg, usage)
    print("="*50)
    return is_ok, msg, code_block, usage

def _llm_augment_patch(
    bug_info: BugInfo,
    llm_client: LLMClient,
    prompt_builder: PromptBuilder,
    plausible_patch: str
) -> Tuple[str, str]:
    prompt = prompt_builder.build_augment_prompt(bug_info.buggy_method, bug_info.error_log, plausible_patch)
    response, usage = llm_client.generate_response(prompt, "patch augment")

    code_block = extract_code_block(response)
    print(f"Patch Augment 接收llm回应: {response}")
    return code_block, usage
    