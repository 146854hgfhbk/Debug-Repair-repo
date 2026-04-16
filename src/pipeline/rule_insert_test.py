from component.ruled_insert_print import ruled_insert_print_pipeline
from defs.bug_info import BugInfo
from llm.llm_client import LLMClient
from llm.prompt_builder import PromptBuilder


def pipeline(
    bug_id: str,
    bug_info: BugInfo,
    llm_client: LLMClient,
    prompt_builder: PromptBuilder
):
    instrumented_code, output = ruled_insert_print_pipeline(
        bug_id=bug_id,
        bug_info=bug_info,
    )