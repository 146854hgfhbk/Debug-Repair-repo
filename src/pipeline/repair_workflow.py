"""Shared paper-aligned session and repair-round orchestration."""

from config import HyperParamConfig


def run_repair_workflow(
    *,
    bug_id,
    bug_info,
    llm_client,
    prompt_builder,
    instrumentation_pipeline,
    direct_repair_pipeline,
    debug_repair_pipeline,
    patch_augment_pipeline,
    status_updater,
    patches_updater,
):
    seed_patch = ""
    final_message = ""

    for session_index in range(HyperParamConfig.MAX_EPOCH):
        print(f"Debugging session {session_index + 1}/{HyperParamConfig.MAX_EPOCH}")

        is_ok, message, code, _ = direct_repair_pipeline(
            bug_id=bug_id,
            bug_info=bug_info,
            llm_client=llm_client,
            prompt_builder=prompt_builder,
        )
        final_message = message
        if is_ok:
            seed_patch = code
            status_updater(bug_id=bug_id, status=True, final_msg=message)
            break

        feedback_history = [
            _feedback_entry(
                0,
                prompt_builder.build_feedback(message, code),
            )
        ]
        try:
            instrumented_code, runtime_output = instrumentation_pipeline(
                bug_id=bug_id,
                bug_info=bug_info,
                llm_client=llm_client,
                prompt_builder=prompt_builder,
            )
        except Exception as exc:
            final_message = (
                "Runtime trace collection failed in debugging session "
                f"{session_index + 1}: {exc}"
            )
            continue

        if not runtime_output or not runtime_output.strip():
            final_message = (
                "Runtime trace unavailable in debugging session "
                f"{session_index + 1}"
            )
            continue

        for repair_round in range(1, HyperParamConfig.MAX_ITER):
            is_ok, message, code, _ = debug_repair_pipeline(
                bug_id=bug_id,
                bug_info=bug_info,
                llm_client=llm_client,
                prompt_builder=prompt_builder,
                instrumented_code=instrumented_code,
                runtime_output=runtime_output,
                feedback="\n\n".join(feedback_history),
            )
            final_message = message
            if is_ok:
                seed_patch = code
                status_updater(bug_id=bug_id, status=True, final_msg=message)
                break

            feedback_history.append(
                _feedback_entry(
                    repair_round,
                    prompt_builder.build_feedback(message, code),
                )
            )

        if seed_patch:
            break

    if not seed_patch:
        status_updater(
            bug_id=bug_id,
            status=False,
            final_msg=final_message,
        )
        return

    plausible_patches = [seed_patch]
    for attempt in range(HyperParamConfig.AUGMENT_SIZE):
        is_ok, _, code, _ = patch_augment_pipeline(
            bug_id=bug_id,
            bug_info=bug_info,
            llm_client=llm_client,
            prompt_builder=prompt_builder,
            plausible_patch=seed_patch,
        )
        if is_ok:
            print(f"Patch augmentation {attempt + 1} succeeded")
            plausible_patches.append(code)
        else:
            print(f"Patch augmentation {attempt + 1} failed")

    patches_updater(
        bug_id=bug_id,
        plausible_patches=plausible_patches,
    )


def _feedback_entry(round_index: int, feedback: str) -> str:
    return f"[Repair attempt {round_index}]\n{feedback}"
