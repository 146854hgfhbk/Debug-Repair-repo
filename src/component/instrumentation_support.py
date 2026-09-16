"""Shared mechanics for the instrumentation strategies described in Section 3.3.

This module centralizes source normalization and buggy-line annotation. Pipeline
selection stays in the hybrid, LLM-only, and rule-only component modules.
"""

import multiprocessing
import time

from utils.java_rule_instrumenter import normalize_method_source


CONSISTENCY_CHECK_TIMEOUT_SECONDS = 10

def add_buggy_line_comments(bug_info, inserted_code: str) -> str:
    """Mark the first unmatched source line for each recorded buggy line."""
    buggy_line_contents = bug_info.buggy_line_contents
    if not inserted_code or not buggy_line_contents:
        return inserted_code

    lines = inserted_code.split("\n")
    annotated_indices = set()

    for content_to_find in buggy_line_contents:
        for index, line in enumerate(lines):
            if index in annotated_indices:
                continue
            if line.strip() == content_to_find:
                if "// Buggy Line" not in lines[index]:
                    lines[index] += " // Buggy Line"
                annotated_indices.add(index)
                break

    return "\n".join(lines)


def build_fault_location_context(bug_info) -> str:
    """Serialize perfect fault-location lines for instrumentation prompting."""
    locations = sorted(set(getattr(bug_info, "relative_buggy_lines", []) or []))
    contents = getattr(bug_info, "buggy_line_contents", []) or []
    entries = []
    for index, line_number in enumerate(locations):
        content = contents[index] if index < len(contents) else ""
        entry = f"Line {line_number}"
        if content:
            entry += f": {content}"
        entries.append(entry)
    return "\n".join(entries)


def check_normalized_source_equivalence(
    original_code: str,
    instrumented_code: str,
    *,
    remove_line_comments: bool,
) -> bool:
    """Run the paper's normalization-stage check in an isolated process."""
    if not original_code or not instrumented_code:
        print("[DEBUG] FAILED: 输入代码为空。")
        return False

    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=normalized_source_equivalence_worker,
        args=(
            original_code,
            instrumented_code,
            result_queue,
            remove_line_comments,
        ),
    )

    start_time = time.time()
    process.start()
    process.join(timeout=CONSISTENCY_CHECK_TIMEOUT_SECONDS)

    if process.is_alive():
        print("  [TIMEOUT] 验证超时！耗时超过 10 秒。")
        print("  -> 正在强制杀死子进程 (Terminate)...")
        process.terminate()
        process.join()
        print("  -> 子进程已终止。判定为验证失败。")
        return False

    if result_queue.empty():
        print("[ERROR] 子进程异常退出，未返回结果。")
        return False

    is_match = result_queue.get()
    elapsed = time.time() - start_time
    if is_match:
        print(f"[DEBUG] 自检通过 (耗时: {elapsed:.4f}s)")
    else:
        print(f"[DEBUG] 自检不匹配 (耗时: {elapsed:.4f}s)")
    return is_match


def normalized_source_equivalence_worker(
    original_code: str,
    instrumented_code: str,
    result_queue,
    remove_line_comments: bool,
) -> None:
    """Compare canonical AST source after removing prints and all comments."""
    try:
        # remove_line_comments is retained for compatibility with older callers.
        normalized_original = normalize_method_source(original_code)
        normalized_instrumented = normalize_method_source(instrumented_code)
        result_queue.put(normalized_original == normalized_instrumented)
    except Exception:
        result_queue.put(False)
