from queue import Queue
from types import SimpleNamespace
from unittest import mock

import pytest

from component import insert_print, llm_insert_print, ruled_insert_print


def _worker_result(worker, original, candidate):
    results = Queue()
    worker(original, candidate, results)
    return results.get_nowait()


def test_buggy_line_annotation_uses_first_exact_unannotated_match():
    bug_info = SimpleNamespace(buggy_line_contents=["value++;", "value++;"])
    source = "value++;\nvalue++;\nreturn value;"
    expected = "value++; // Buggy Line\nvalue++; // Buggy Line\nreturn value;"

    assert insert_print._add_buggy_line_comments(bug_info, source) == expected
    assert llm_insert_print._add_buggy_line_comments(bug_info, source) == expected
    assert ruled_insert_print._add_buggy_line_comments(bug_info, source) == expected


def test_hybrid_consistency_ignores_comment_differences():
    original = "int f() { return 1; }"
    candidate = "int f() { // generated\n return 1; }"

    assert _worker_result(
        insert_print._check_insert_print_subfunc,
        original,
        candidate,
    )


def test_llm_only_consistency_ignores_line_comments():
    original = "int f() { return 1; }"
    candidate = "int f() { // generated\n return 1; }"

    assert _worker_result(
        llm_insert_print._check_insert_print_subfunc,
        original,
        candidate,
    )


def test_consistency_preserves_whitespace_inside_string_literals():
    original = 'String f() { return "a b"; }'
    candidate = 'String f() { return "ab"; }'

    assert not _worker_result(
        insert_print._check_insert_print_subfunc,
        original,
        candidate,
    )


def test_consistency_does_not_hide_removal_of_existing_business_print():
    original = (
        'void f() { System.out.println("audit"); doWork(); }'
    )
    candidate = (
        'void f() { System.out.println("// DEBUG: entered"); doWork(); }'
    )

    assert not _worker_result(
        insert_print._check_insert_print_subfunc,
        original,
        candidate,
    )


def test_consistency_removes_only_recognized_instrumentation_prints():
    original = (
        'void f() { System.out.println("audit"); doWork(); }'
    )
    candidate = (
        'void f() { System.out.println("// DEBUG: entered"); '
        'System.out.println("audit"); doWork(); '
        'System.out.println("// DEBUG_MARKER_END"); }'
    )

    assert _worker_result(
        insert_print._check_insert_print_subfunc,
        original,
        candidate,
    )


def test_hybrid_pipeline_falls_back_only_after_llm_attempts(monkeypatch):
    bug_info = SimpleNamespace()
    llm_candidates = iter([("candidate-1", {}), ("candidate-2", {})])
    rule_calls = []

    monkeypatch.setattr(insert_print.HyperParamConfig, "INSERT_MAX_ATTEMPT", 2)
    monkeypatch.setattr(
        insert_print,
        "_llm_insert_print",
        lambda *args: next(llm_candidates),
    )
    monkeypatch.setattr(insert_print, "_check_insert_print", lambda *args: False)
    monkeypatch.setattr(
        insert_print,
        "rule_insert_print",
        lambda info, start, end: rule_calls.append((info, start, end)) or "rule",
    )
    monkeypatch.setattr(
        insert_print,
        "_add_buggy_line_comments",
        lambda info, source: source,
    )
    monkeypatch.setattr(insert_print, "collect_output", lambda *args: "trace")
    monkeypatch.setattr(insert_print, "output_log", lambda *args: None)

    result = insert_print.insert_print_pipeline("Chart-1", bug_info, object(), object())

    assert result == ("rule", "trace")
    assert rule_calls == [
        (bug_info, insert_print.START_MARKER, insert_print.END_MARKER)
    ]


def test_llm_only_pipeline_skips_collection_after_rejected_candidates(monkeypatch):
    bug_info = SimpleNamespace()
    collection_calls = []

    monkeypatch.setattr(llm_insert_print.HyperParamConfig, "INSERT_MAX_ATTEMPT", 1)
    monkeypatch.setattr(
        llm_insert_print,
        "_llm_insert_print",
        lambda *args: ("rejected", {}),
    )
    monkeypatch.setattr(
        llm_insert_print,
        "_check_insert_print",
        lambda *args: False,
    )
    monkeypatch.setattr(
        llm_insert_print,
        "_add_buggy_line_comments",
        lambda info, source: source,
    )
    monkeypatch.setattr(
        llm_insert_print,
        "collect_output",
        lambda *args: collection_calls.append(args),
    )
    monkeypatch.setattr(llm_insert_print, "output_log", lambda *args: None)

    result = llm_insert_print.llm_insert_print_pipeline(
        "Chart-1",
        bug_info,
        object(),
        object(),
    )

    assert result == ("rejected", "")
    assert collection_calls == []


def test_rule_only_pipeline_uses_rule_markers_without_setting_repair_status(
    monkeypatch,
):
    bug_info = SimpleNamespace()
    rule_calls = []

    monkeypatch.setattr(
        ruled_insert_print,
        "rule_insert_print",
        lambda info, start, end: rule_calls.append((info, start, end)) or "rule",
    )
    monkeypatch.setattr(
        ruled_insert_print,
        "_add_buggy_line_comments",
        lambda info, source: source,
    )
    monkeypatch.setattr(
        ruled_insert_print,
        "collect_output",
        lambda *args: "trace",
    )
    monkeypatch.setattr(ruled_insert_print, "output_log", lambda *args: None)
    result = ruled_insert_print.ruled_insert_print_pipeline("Chart-1", bug_info)

    assert result == ("rule", "trace")
    assert rule_calls == [
        (bug_info, ruled_insert_print.START_MARKER, ruled_insert_print.END_MARKER)
    ]


@pytest.mark.parametrize(
    "module,pipeline_name",
    [
        (insert_print, "insert_print_pipeline"),
        (llm_insert_print, "llm_insert_print_pipeline"),
        (ruled_insert_print, "ruled_insert_print_pipeline"),
    ],
)
def test_instrumentation_pipelines_propagate_remote_infrastructure_failure(
    monkeypatch, module, pipeline_name
):
    from utils.remote_validation import RemoteValidationError

    bug_info = SimpleNamespace()
    monkeypatch.setattr(module, "output_log", lambda *args: None)
    monkeypatch.setattr(
        module,
        "_add_buggy_line_comments",
        lambda info, source: source,
    )
    monkeypatch.setattr(
        module,
        "collect_output",
        mock.Mock(side_effect=RemoteValidationError("validator unavailable")),
    )

    if module is ruled_insert_print:
        monkeypatch.setattr(module, "rule_insert_print", lambda *args: "instrumented")
        arguments = ("Chart-1", bug_info)
    else:
        monkeypatch.setattr(module.HyperParamConfig, "INSERT_MAX_ATTEMPT", 1)
        monkeypatch.setattr(module, "_llm_insert_print", lambda *args: ("instrumented", {}))
        monkeypatch.setattr(module, "_check_insert_print", lambda *args: True)
        monkeypatch.setattr(module, "check_instrumented_compiles", lambda *args: (True, ""))
        arguments = ("Chart-1", bug_info, object(), object())

    with pytest.raises(RemoteValidationError):
        getattr(module, pipeline_name)(*arguments)


def test_hybrid_pipeline_retries_candidates_that_fail_compilation(monkeypatch):
    bug_info = SimpleNamespace()
    llm_candidates = iter([("candidate-1", {}), ("candidate-2", {})])
    compile_calls = []
    rule_calls = []

    monkeypatch.setattr(insert_print.HyperParamConfig, "INSERT_MAX_ATTEMPT", 2)
    monkeypatch.setattr(
        insert_print,
        "_llm_insert_print",
        lambda *args: next(llm_candidates),
    )
    monkeypatch.setattr(insert_print, "_check_insert_print", lambda *args: True)
    monkeypatch.setattr(
        insert_print,
        "check_instrumented_compiles",
        lambda bug_id, info, source: compile_calls.append(source)
        or (False, "Compile failed"),
        raising=False,
    )
    monkeypatch.setattr(
        insert_print,
        "rule_insert_print",
        lambda info, start, end: rule_calls.append((start, end)) or "rule",
    )
    monkeypatch.setattr(
        insert_print,
        "_add_buggy_line_comments",
        lambda info, source: source,
    )
    monkeypatch.setattr(insert_print, "collect_output", lambda *args: "trace")
    monkeypatch.setattr(insert_print, "output_log", lambda *args: None)

    result = insert_print.insert_print_pipeline(
        "Chart-1", bug_info, object(), object()
    )

    assert result == ("rule", "trace")
    assert compile_calls == ["candidate-1", "candidate-2"]
    assert rule_calls == [(insert_print.START_MARKER, insert_print.END_MARKER)]


def test_llm_only_pipeline_rejects_candidate_that_fails_compilation(monkeypatch):
    bug_info = SimpleNamespace()
    collection_calls = []

    monkeypatch.setattr(llm_insert_print.HyperParamConfig, "INSERT_MAX_ATTEMPT", 1)
    monkeypatch.setattr(
        llm_insert_print,
        "_llm_insert_print",
        lambda *args: ("candidate", {}),
    )
    monkeypatch.setattr(llm_insert_print, "_check_insert_print", lambda *args: True)
    monkeypatch.setattr(
        llm_insert_print,
        "check_instrumented_compiles",
        lambda *args: (False, "Compile failed"),
        raising=False,
    )
    monkeypatch.setattr(
        llm_insert_print,
        "_add_buggy_line_comments",
        lambda info, source: source,
    )
    monkeypatch.setattr(
        llm_insert_print,
        "collect_output",
        lambda *args: collection_calls.append(args),
    )
    monkeypatch.setattr(llm_insert_print, "output_log", lambda *args: None)

    result = llm_insert_print.llm_insert_print_pipeline(
        "Chart-1", bug_info, object(), object()
    )

    assert result == ("candidate", "")
    assert collection_calls == []


@pytest.mark.parametrize(
    "llm_insert",
    [insert_print._llm_insert_print, llm_insert_print._llm_insert_print],
)
def test_instrumentation_prompt_receives_perfect_fault_location(llm_insert):
    class RecordingPromptBuilder:
        def __init__(self):
            self.arguments = None

        def build_insert_print_prompt(self, *arguments):
            self.arguments = arguments
            return [{"role": "user", "content": "instrument"}]

    class FakeClient:
        def generate_response(self, prompt, prompt_name):
            return "```java\nint value() { return 1; }\n```", {}

    bug_info = SimpleNamespace(
        buggy_method="int value() {\n    return 1;\n}",
        sliced_trigger_test="void failingTest() {}",
        error_log="failure",
        relative_buggy_lines=[41],
        buggy_line_contents=["return 1;"],
    )
    prompt_builder = RecordingPromptBuilder()

    llm_insert(
        bug_info,
        FakeClient(),
        prompt_builder,
        "// START_DEBUG",
        "// END_DEBUG",
    )

    assert "return 1; // Buggy Line" in prompt_builder.arguments[0]
    assert prompt_builder.arguments[5] == "Line 41: return 1;"
