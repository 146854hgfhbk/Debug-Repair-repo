from component.debug_repair import debug_repair_pipeline
from component.insert_print import insert_print_pipeline
from component.direct_repair import direct_repair_pipeline
from component.patch_augment import patch_augment_pipeline
from llm.llm_client import LLMClient
from llm.prompt_builder import PromptBuilder

from utils.output_logger import update_status_and_final_msg, update_plausible_patches

from defs.bug_info import BugInfo
from config import HyperParamConfig

def pipeline(
    bug_id: str,
    bug_info: BugInfo,
    llm_client: LLMClient,
    prompt_builder: PromptBuilder
):
    instrumented_code, output = insert_print_pipeline(
        bug_id=bug_id,
        bug_info=bug_info,
        llm_client=llm_client,
        prompt_builder=prompt_builder
    )

    fix = False
    seed_patch = ""
    plausible_patches = []

    for epoch in range(HyperParamConfig.MAX_EPOCH):
        print(f"第 {epoch} 轮修复")

        is_ok, msg, code, usage = direct_repair_pipeline(
            bug_id=bug_id,
            bug_info=bug_info,
            llm_client=llm_client,
            prompt_builder=prompt_builder
        )

        if is_ok:
            update_status_and_final_msg(bug_id=bug_id, status=True, final_msg=msg)
            seed_patch = code
            fix = True
            break
        
        feedback = prompt_builder.build_feedback(msg, code)

        for attempt in range(HyperParamConfig.MAX_ITER):
            is_ok, msg, code, usage = debug_repair_pipeline(
                bug_id=bug_id,
                bug_info=bug_info,
                llm_client=llm_client,
                prompt_builder=prompt_builder,
                instrumented_code=instrumented_code,
                runtime_output=output,
                feedback = feedback
            )

            if is_ok:
                update_status_and_final_msg(bug_id=bug_id, status=True, final_msg=msg)
                seed_patch = code
                fix = True
                break

            feedback = prompt_builder.build_feedback(msg, code)

        if fix == True:
            break
    
    if fix == False:
        update_status_and_final_msg(bug_id=bug_id, status=False, final_msg=msg)
        return
    else:
        plausible_patches.append(seed_patch)

        for attempt in range(HyperParamConfig.AUGMENT_SIZE):
            is_ok, msg, code, usage = patch_augment_pipeline(
                bug_id=bug_id,
                bug_info=bug_info,
                llm_client=llm_client,
                prompt_builder=prompt_builder,
                plausible_patch=seed_patch
            )

            if is_ok:
                print(f"第{attempt + 1}次补丁增强成功")
                plausible_patches.append(code)
            else:
                print(f"第{attempt + 1}次补丁增强失败")

    update_plausible_patches(bug_id=bug_id, plausible_patches=plausible_patches)

