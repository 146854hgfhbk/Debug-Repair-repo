"""Deterministic rule-only instrumentation used by the paper's ablation."""

from component.instrumentation_support import add_buggy_line_comments
from defs.bug_info import BugInfo
from utils.collect_output import collect_output
from utils.output_logger import output_log
from utils.rule_based_insert_print import rule_insert_print


START_MARKER = "// START_DEBUG"
END_MARKER = "// END_DEBUG"


def ruled_insert_print_pipeline(
    bug_id: str,
    bug_info: BugInfo,
):
    inserted_code = rule_insert_print(bug_info, START_MARKER, END_MARKER)
    instrumented_code = _add_buggy_line_comments(bug_info, inserted_code)

    output = ""
    try:
        output = collect_output(bug_id, bug_info, instrumented_code)
    except Exception as exc:
        from utils.remote_validation import RemoteValidationError
        if isinstance(exc, RemoteValidationError):
            raise
        print(f"  [ERROR] Runtime trace collection failed: {exc}")

    output_log(bug_id, "ruled_insert_print", instrumented_code, output)
    return instrumented_code, output


def _add_buggy_line_comments(
    bug_info: BugInfo,
    inserted_code: str,
) -> str:
    """Compatibility wrapper for buggy-line annotation."""
    return add_buggy_line_comments(bug_info, inserted_code)
