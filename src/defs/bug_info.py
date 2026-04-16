from config import BasicConfig
from utils.load_json import load_json
from typing import List, Dict

class BugInfo:
    bug_id = ""
    buggy_method = ""
    trigger_test = ""
    sliced_trigger_test = ""
    error_log = ""

    start_line = 0
    end_line = 0

    relative_buggy_lines: List[int] = []
    buggy_line_contents: List[str] = []

    def __init__(self, bug_id):
        bug_info = load_json(BasicConfig.BUG_INFO_JSON)
        failing_test = load_json(BasicConfig.FAILING_TEST_JSON)
        file_hash = load_json(BasicConfig.FILE_HASH_JSON)

        self.bug_id = bug_id
        self.buggy_method = bug_info[bug_id].get("buggy", "")
        failing_tests = failing_test[bug_id].get("failing_tests", "")
        self.trigger_test = self._build_full_test(failing_tests)
        self.sliced_trigger_test = self._build_sliced_test(failing_tests)
        self.error_log = self._build_error_log(failing_test[bug_id].get("failing_tests", []))

        self.start_line = bug_info[bug_id].get("start", 0)
        self.end_line = bug_info[bug_id].get("end", 0)

        self.relative_buggy_lines = bug_info[bug_id].get("location", [])

        method_lines = self.buggy_method.split("\n")
        for line in sorted(set(self.relative_buggy_lines)):
            relative_index = line - self.start_line + 1
            if 1 <= relative_index <= len(method_lines):
                self.buggy_line_contents.append(method_lines[relative_index - 1].strip())

    def display_bug_info(self):
        print(f"Bug ID: {self.bug_id}\n")
        print(f"Buggy Method: {self.buggy_method}\n")
        print(f"Trigger Test: {self.trigger_test}\n")
        print(f"Sliced Trigger Test: {self.sliced_trigger_test}\n")
        print(f"Error Log: {self.error_log}\n")
        print(f"Start Line: {self.start_line}\n")
        print(f"End Line: {self.end_line}\n")
        print(f"Relative Buggy Lines: {self.relative_buggy_lines}\n")
        print(f"Buggy Line Contents: {self.buggy_line_contents}\n")

    def _build_error_log(self, failing_tests: List[Dict]) -> str:
        entries: List[str] = []
        for index, test in enumerate(failing_tests or [], 1):
            lines: List[str] = []
            method_name = test.get("test_method_name") or f"Test#{index}"
            test_file = test.get("test_file_path")
            failure_line = test.get("failure_line") or test.get("failing_line")
            failure_message = test.get("failure_message")

            lines.append(f"[Test] {method_name}")
            if test_file:
                lines.append(f"[Class] {test_file}")
            if failure_line:
                lines.append(f"[Failure line] {failure_line}")
            if failure_message:
                lines.append(f"[Failure message] {failure_message}")

            entry = "\n".join(lines).strip()
            if entry:
                entries.append(entry)

        return "\n\n".join(entries).strip()
    
    def _build_sliced_test(self, failing_tests: List[Dict]) -> str:
        """
        将 sliced_test 与依赖组合为一个字符串，用于 Prompt 的 {test_context}
        """
        if not failing_tests:
            return ""

        blocks: List[str] = []
        for index, test in enumerate(failing_tests, 1):
            parts: List[str] = []
            method_name = test.get("test_method_name") or f"Test#{index}"
            parts.append(f"// Failing Test #{index}: {method_name}")

            sliced = (test.get("sliced_test") or "").strip()
            if sliced:
                parts.append(sliced)

            dependencies = test.get("dependencies") or {}
            dep_methods = dependencies.get("methods") or []
            dep_vars = dependencies.get("variables") or []

            clean_methods = [m.strip() for m in dep_methods if isinstance(m, str) and m.strip()]
            clean_vars = [v.strip() for v in dep_vars if isinstance(v, str) and v.strip()]

            if clean_methods:
                parts.append("// Dependent methods:")
                parts.append("\n\n".join(clean_methods))
            if clean_vars:
                parts.append("// Dependent variables:")
                parts.append("\n".join(clean_vars))

            block = "\n".join(parts).strip()
            if block:
                blocks.append(block)

        return "\n\n".join(blocks).strip()

    def _build_full_test(self, failing_tests: List[Dict]) -> str:
        """
        将 full_test 与依赖组合为一个字符串，用于 Prompt 的 {test_context}
        """
        if not failing_tests:
            return ""

        blocks: List[str] = []
        for index, test in enumerate(failing_tests, 1):
            parts: List[str] = []
            method_name = test.get("test_method_name") or f"Test#{index}"
            parts.append(f"// Failing Test #{index}: {method_name}")

            sliced = (test.get("full_test") or "").strip()
            if sliced:
                parts.append(sliced)

            dependencies = test.get("dependencies") or {}
            dep_methods = dependencies.get("methods") or []
            dep_vars = dependencies.get("variables") or []

            clean_methods = [m.strip() for m in dep_methods if isinstance(m, str) and m.strip()]
            clean_vars = [v.strip() for v in dep_vars if isinstance(v, str) and v.strip()]

            if clean_methods:
                parts.append("// Dependent methods:")
                parts.append("\n\n".join(clean_methods))
            if clean_vars:
                parts.append("// Dependent variables:")
                parts.append("\n".join(clean_vars))

            block = "\n".join(parts).strip()
            if block:
                blocks.append(block)

        return "\n\n".join(blocks).strip()