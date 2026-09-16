"""LLM-only instrumentation used by the paper's ablation pipeline."""

from component.instrumentation_support import (
    add_buggy_line_comments,
    build_fault_location_context,
    check_normalized_source_equivalence,
    normalized_source_equivalence_worker,
)
from config import HyperParamConfig
from defs.bug_info import BugInfo
from llm.llm_client import LLMClient
from llm.prompt_builder import PromptBuilder
from utils.collect_output import collect_output, check_instrumented_compiles
from utils.extract_code import extract_code_block
from utils.output_logger import output_log


START_MARKER = "// DEBUG_MARKER_START"
END_MARKER = "// DEBUG_MARKER_END"


def llm_insert_print_pipeline(
    bug_id: str,
    bug_info: BugInfo,
    llm_client: LLMClient,
    prompt_builder: PromptBuilder,
):
    candidate_is_consistent = False
    inserted_code = ""

    for attempt in range(HyperParamConfig.INSERT_MAX_ATTEMPT):
        print(f"尝试插入输出: 第{attempt + 1}/{HyperParamConfig.INSERT_MAX_ATTEMPT}次")

        inserted_code, usage_info = _llm_insert_print(
            bug_info,
            llm_client,
            prompt_builder,
            START_MARKER,
            END_MARKER,
        )
        output_log(bug_id, "insert_print", inserted_code, "", usage_info)

        if not _check_insert_print(bug_info, inserted_code):
            continue

        compiles, compile_message = check_instrumented_compiles(
            bug_id,
            bug_info,
            inserted_code,
        )
        if not compiles:
            print(f"  [COMPILE CHECK FAILED] {compile_message}")
            continue

        candidate_is_consistent = True
        break

    instrumented_code = _add_buggy_line_comments(bug_info, inserted_code)
    print("-> 插桩完成")
    print(f"-> 插桩代码: \n{instrumented_code}")

    output = ""
    if candidate_is_consistent:
        try:
            output = collect_output(bug_id, bug_info, instrumented_code)
        except Exception as exc:
            from utils.remote_validation import RemoteValidationError
            if isinstance(exc, RemoteValidationError):
                raise
            print(f"  [ERROR] 收集输出失败: {exc}")
            output = ""

    output_log(bug_id, "llm_insert_print", instrumented_code, output)

    return instrumented_code, output


def _llm_insert_print(
    bug_info: BugInfo,
    llm_client: LLMClient,
    prompt_builder: PromptBuilder,
    start_marker: str,
    end_marker: str,
):
    prompt_buggy_method = add_buggy_line_comments(
        bug_info,
        bug_info.buggy_method,
    )
    prompt = prompt_builder.build_insert_print_prompt(
        prompt_buggy_method,
        bug_info.sliced_trigger_test,
        bug_info.error_log,
        start_marker,
        end_marker,
        build_fault_location_context(bug_info),
    )
    response, usage = llm_client.generate_response(prompt, "insert_print")

    print("-" * 50)
    print(response)
    print("-" * 50)

    code_block = extract_code_block(response)

    print("-" * 50)
    print(code_block)
    print("-" * 50)
    return code_block, usage


def _check_insert_print(
    bug_info: BugInfo,
    inserted_code: str,
) -> bool:
    return check_normalized_source_equivalence(
        bug_info.buggy_method,
        inserted_code,
        remove_line_comments=True,
    )


def _add_buggy_line_comments(
    bug_info: BugInfo,
    inserted_code: str,
) -> str:
    """Compatibility wrapper for buggy-line annotation."""
    return add_buggy_line_comments(bug_info, inserted_code)


def _check_insert_print_subfunc(
    original_code: str,
    instrumented_code: str,
    result_queue,
):
    """Compatibility worker preserving LLM-only comment handling."""
    normalized_source_equivalence_worker(
        original_code,
        instrumented_code,
        result_queue,
        True,
    )
