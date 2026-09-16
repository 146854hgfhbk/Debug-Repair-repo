from types import SimpleNamespace

import pytest

from component import debug_repair, direct_repair, patch_augment


class RecordingPromptBuilder:
    def __init__(self):
        self.arguments = None

    def _record(self, *arguments):
        self.arguments = arguments
        return [{"role": "user", "content": "repair"}]

    build_direct_repair_prompt = _record
    build_debug_repair_prompt = _record
    build_augment_prompt = _record


class FakeClient:
    def generate_response(self, prompt, prompt_name):
        return "```java\nint value() { return 1; }\n```", {}


@pytest.fixture
def bug_info():
    return SimpleNamespace(
        buggy_method="int value() {\n    return 0;\n}",
        sliced_trigger_test="void failingTest() {}",
        error_log="failure",
        relative_buggy_lines=[2],
        buggy_line_contents=["return 0;"],
    )


@pytest.mark.parametrize(
    "invoke",
    [
        lambda info, client, builder: direct_repair._llm_direct_repair(
            info, client, builder
        ),
        lambda info, client, builder: debug_repair._llm_debug_repair(
            info, client, builder, "instrumented", "trace", "feedback"
        ),
        lambda info, client, builder: patch_augment._llm_augment_patch(
            info, client, builder, "plausible"
        ),
    ],
)
def test_repair_prompts_receive_perfect_fault_location(
    bug_info,
    invoke,
):
    builder = RecordingPromptBuilder()

    invoke(bug_info, FakeClient(), builder)

    assert "return 0; // Buggy Line" in builder.arguments[0]
