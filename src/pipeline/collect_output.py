from component.run_and_collect_output import run_and_collect_output_pipeline
from defs.bug_info import BugInfo
from llm.llm_client import LLMClient
from llm.prompt_builder import PromptBuilder

from config import BasicConfig

import json


def pipeline(
    bug_id: str,
    bug_info: BugInfo,
    llm_client: LLMClient,
    prompt_builder: PromptBuilder
):
    with open(BasicConfig.INSTRUMENTED_CODE_INPUT_PATH, 'r') as f:
        instrumented_code = json.load(f)
    
    if not instrumented_code.get(bug_id):
        return
    
    instrumented_code = instrumented_code[bug_id]

    instrumented_code, output = run_and_collect_output_pipeline(
        bug_id=bug_id,
        bug_info=bug_info,
        instrumented_code=instrumented_code
    )