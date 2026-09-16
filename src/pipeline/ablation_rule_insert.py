from component.debug_repair import debug_repair_pipeline
from component.llm_insert_print import llm_insert_print_pipeline
from component.direct_repair import direct_repair_pipeline
from component.patch_augment import patch_augment_pipeline
from llm.llm_client import LLMClient
from llm.prompt_builder import PromptBuilder

from utils.output_logger import update_status_and_final_msg, update_plausible_patches

from defs.bug_info import BugInfo
from config import HyperParamConfig
from pipeline.repair_workflow import run_repair_workflow

def pipeline(
    bug_id: str,
    bug_info: BugInfo,
    llm_client: LLMClient,
    prompt_builder: PromptBuilder
):
    return run_repair_workflow(
        bug_id=bug_id,
        bug_info=bug_info,
        llm_client=llm_client,
        prompt_builder=prompt_builder,
        instrumentation_pipeline=llm_insert_print_pipeline,
        direct_repair_pipeline=direct_repair_pipeline,
        debug_repair_pipeline=debug_repair_pipeline,
        patch_augment_pipeline=patch_augment_pipeline,
        status_updater=update_status_and_final_msg,
        patches_updater=update_plausible_patches,
    )
