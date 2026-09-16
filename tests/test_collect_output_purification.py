import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from unittest import mock

from utils import collect_output


def test_single_test_runner_supports_junit3_without_junit4_compile_dependency():
    source = collect_output.SINGLE_TEST_RUNNER_SOURCE

    assert "import org.junit" not in source
    assert 'Class.forName("org.junit.runner.JUnitCore")' in source
    assert 'Class.forName("junit.framework.TestCase")' in source


def test_cli_27_metadata_contains_valid_inherited_purified_test():
    metadata_path = (
        Path(__file__).parents[1] / "data" / "bug_info" / "failing_test.json"
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))["Cli-27"]
    failing_test = metadata["failing_tests"][0]

    assert failing_test["test_file_path"] == "org.apache.commons.cli.BasicParserTest"
    assert (
        failing_test["test_source_file_path"]
        == "org.apache.commons.cli.ParserTestCase"
    )
    assert "assertEquals(\"selected option\", \"bar\"" in failing_test["sliced_test"]
    assert "assertTrue(cl.hasOption" not in failing_test["sliced_test"]


def test_selects_purified_test_by_class_and_method():
    bug_info = SimpleNamespace(
        bug_id="Chart-1",
        failing_tests=[
            {
                "test_file_path": "example.FirstTest",
                "test_method_name": "firstFailure",
                "sliced_test": "void firstFailure() { assertTrue(false); }",
            },
            {
                "test_file_path": "example.TargetTest",
                "test_method_name": "targetFailure",
                "sliced_test": "void targetFailure() { assertEquals(1, actual); }",
            },
        ],
    )

    result = collect_output._load_test_function_code(
        bug_info,
        "example.TargetTest",
        "targetFailure",
    )

    assert result == "void targetFailure() { assertEquals(1, actual); }"


def test_rejects_missing_purified_test_even_when_legacy_file_exists(
    monkeypatch,
    tmp_path,
):
    (tmp_path / "Chart-1.java").write_text(
        "void targetFailure() { originalNoise(); }",
        encoding="utf-8",
    )
    monkeypatch.setattr(collect_output.BasicConfig, "TEST_PATH", str(tmp_path))
    bug_info = SimpleNamespace(
        bug_id="Chart-1",
        failing_tests=[
            {
                "test_file_path": "example.TargetTest",
                "test_method_name": "targetFailure",
                "sliced_test": "",
            }
        ],
    )

    with pytest.raises(ValueError, match="Purified test unavailable"):
        collect_output._load_test_function_code(
            bug_info,
            "example.TargetTest",
            "targetFailure",
        )


def test_rejects_non_matching_purified_test():
    bug_info = SimpleNamespace(
        bug_id="Chart-1",
        failing_tests=[
            {
                "test_file_path": "example.OtherTest",
                "test_method_name": "otherFailure",
                "sliced_test": "void otherFailure() {}",
            }
        ],
    )

    with pytest.raises(ValueError, match="Purified test unavailable"):
        collect_output._load_test_function_code(
            bug_info,
            "example.TargetTest",
            "targetFailure",
        )


def test_selects_first_exported_trigger_with_a_non_empty_purified_slice():
    bug_info = SimpleNamespace(
        bug_id="Chart-1",
        failing_tests=[
            {
                "test_file_path": "example.EmptyTest",
                "test_method_name": "emptyFailure",
                "sliced_test": "",
            },
            {
                "test_file_path": "example.TargetTest",
                "test_method_name": "targetFailure",
                "sliced_test": "void targetFailure() { assertEquals(1, actual); }",
            },
        ],
    )

    selected = collect_output._select_purified_trigger(
        bug_info,
        [
            "example.EmptyTest::emptyFailure",
            "example.TargetTest::targetFailure",
        ],
    )

    assert selected == (
        "example.TargetTest",
        "targetFailure",
        "void targetFailure() { assertEquals(1, actual); }",
        "example.TargetTest",
    )


def test_selects_declaring_source_class_for_inherited_trigger():
    bug_info = SimpleNamespace(
        bug_id="Cli-27",
        failing_tests=[
            {
                "test_file_path": "org.apache.commons.cli.BasicParserTest",
                "test_source_file_path": "org.apache.commons.cli.ParserTestCase",
                "test_method_name": "testOptionGroupLong",
                "sliced_test": "void testOptionGroupLong() { assertTrue(false); }",
            }
        ],
    )

    selected = collect_output._select_purified_trigger(
        bug_info,
        ["org.apache.commons.cli.BasicParserTest::testOptionGroupLong"],
    )

    assert selected == (
        "org.apache.commons.cli.BasicParserTest",
        "testOptionGroupLong",
        "void testOptionGroupLong() { assertTrue(false); }",
        "org.apache.commons.cli.ParserTestCase",
    )


def test_rejects_metadata_that_is_not_an_exported_trigger():
    bug_info = SimpleNamespace(
        bug_id="Chart-1",
        failing_tests=[
            {
                "test_file_path": "example.TargetTest",
                "test_method_name": "targetFailure",
                "sliced_test": "void targetFailure() {}",
            }
        ],
    )

    with pytest.raises(ValueError, match="exported trigger"):
        collect_output._select_purified_trigger(
            bug_info,
            ["example.OtherTest::otherFailure"],
        )


def test_runs_only_the_selected_trigger_method(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        if args[0] == "defects4j" and args[1] == "compile":
            return Mock(returncode=0, stdout="", stderr="")
        if args[0] == "defects4j" and args[1] == "export":
            return Mock(returncode=0, stdout="fake-test-classpath", stderr="")
        if args[0] == "javac":
            return Mock(returncode=0, stdout="", stderr="")
        return Mock(
            returncode=1,
            stdout=(
                "Now runtime output for trigger test begin:\n"
                "========Test Case Start========\n"
                "// DEBUG: value = 1\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(collect_output.subprocess, "run", fake_run)

    success, output = collect_output._run_and_collect_output(
        "example.TargetTest",
        "targetFailure",
        str(tmp_path),
    )

    assert not success
    assert "// DEBUG: value = 1" in output
    assert calls[3][0][-3:] == [
        "SingleTestRunner",
        "example.TargetTest",
        "targetFailure",
    ]
    assert all(call[1].get("shell") is not True for call in calls)
    assert not list(tmp_path.glob(".debugrepair-runner-*"))


def test_replacing_annotated_slice_removes_original_method_annotations(tmp_path):
    test_file = tmp_path / "TargetTest.java"
    test_file.write_text(
        "class TargetTest {\n"
        "    @Deprecated\n"
        "    @org.junit.Test\n"
        "    public void targetFailure() { originalNoise(); }\n"
        "}\n",
        encoding="ISO-8859-1",
    )
    sliced = (
        "@org.junit.Test(timeout = 1000)\n"
        "public void targetFailure() { assertTrue(false); }"
    )

    assert collect_output._replace_test_function(
        str(test_file),
        "targetFailure",
        sliced,
    )

    result = test_file.read_text(encoding="ISO-8859-1")
    assert result.count("@org.junit.Test") == 1
    assert "@Deprecated" not in result
    marker = 'System.out.println("\\nNow runtime output for trigger test begin:\\n");'
    assert result.index("public void targetFailure()") < result.index(marker)
    assert result.index(marker) < result.index("assertTrue(false);")
def test_runtime_collection_uses_configured_defects4j(monkeypatch):
    monkeypatch.setattr(
        "utils.collect_output.ValidatorConfig.DEFECTS4J_EXECUTABLE",
        "/opt/defects4j-3.0",
    )
    run = mock.Mock(return_value=mock.Mock(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr("utils.collect_output.subprocess.run", run)

    collect_output._run_defects4j(["export", "-p", "tests.trigger"])

    assert run.call_args.args[0][0] == "/opt/defects4j-3.0"
