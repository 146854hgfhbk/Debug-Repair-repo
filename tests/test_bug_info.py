from defs import bug_info as bug_info_module


def test_buggy_line_contents_are_isolated_between_instances(monkeypatch):
    bug_data = {
        "First-1": {
            "buggy": "int first() {\n    return 1;\n}",
            "start": 10,
            "end": 12,
            "location": [11],
        },
        "Second-1": {
            "buggy": "int second() {\n    return 2;\n}",
            "start": 20,
            "end": 22,
            "location": [21],
        },
    }
    failing_data = {
        "First-1": {"failing_tests": []},
        "Second-1": {"failing_tests": []},
    }

    def fake_load(path):
        if path == bug_info_module.BasicConfig.BUG_INFO_JSON:
            return bug_data
        if path == bug_info_module.BasicConfig.FAILING_TEST_JSON:
            return failing_data
        return {}

    monkeypatch.setattr(bug_info_module, "load_json", fake_load)

    first = bug_info_module.BugInfo("First-1")
    first_contents = list(first.buggy_line_contents)
    second = bug_info_module.BugInfo("Second-1")

    assert first.buggy_line_contents is not second.buggy_line_contents
    assert first.buggy_line_contents == first_contents == ["return 1;"]
    assert second.buggy_line_contents == ["return 2;"]


def test_bug_info_preserves_structured_failing_tests(monkeypatch):
    failing_tests = [
        {
            "test_file_path": "example.TargetTest",
            "test_method_name": "targetFailure",
            "sliced_test": "void targetFailure() {}",
        }
    ]

    def fake_load(path):
        if path == bug_info_module.BasicConfig.BUG_INFO_JSON:
            return {
                "Chart-1": {
                    "buggy": "int value() { return 1; }",
                    "start": 1,
                    "end": 1,
                    "location": [1],
                }
            }
        if path == bug_info_module.BasicConfig.FAILING_TEST_JSON:
            return {"Chart-1": {"failing_tests": failing_tests}}
        return {}

    monkeypatch.setattr(bug_info_module, "load_json", fake_load)

    result = bug_info_module.BugInfo("Chart-1")

    assert result.failing_tests == failing_tests
    assert result.failing_tests is not failing_tests
