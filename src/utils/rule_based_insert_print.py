from defs.bug_info import BugInfo
from utils.java_rule_instrumenter import instrument_method_source


def _normalize_marker(marker: str, fallback: str) -> str:
    value = (marker or "").strip()
    if not value:
        return fallback
    if value.startswith("//"):
        return value
    return f"// {value.lstrip('/').strip()}"


def rule_based_instrument_method(
    bug_info: BugInfo,
    start_marker: str = "// START_DEBUG",
    end_marker: str = "// END_DEBUG",
) -> str:
    """Instrument the buggy callable with the JavaParser rule engine."""
    buggy_method = (getattr(bug_info, "buggy_method", "") or "").strip()
    if not buggy_method:
        raise ValueError("buggy_method is empty")

    return instrument_method_source(
        buggy_method,
        _normalize_marker(start_marker, "// START_DEBUG"),
        _normalize_marker(end_marker, "// END_DEBUG"),
    )


def rule_insert_print(
    bug_info: BugInfo,
    start_marker: str = "// START_DEBUG",
    end_marker: str = "// END_DEBUG",
) -> str:
    """Compatibility entry point used by the existing instrumentation pipelines."""
    try:
        return rule_based_instrument_method(bug_info, start_marker, end_marker)
    except Exception as exc:
        import traceback

        print(f"Instrumentation failed: {exc}")
        print(traceback.format_exc())
        return ""
