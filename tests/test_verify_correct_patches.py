import json
import tempfile
import unittest
from pathlib import Path

from verify_correct_patches import (
    browser_compatible_headers,
    build_patch_records,
    classify_response,
    group_pending_by_bug,
    manual_result_entries,
    normalize_code,
    result_entry,
    summarize_results,
)


class VerifyCorrectPatchesTests(unittest.TestCase):
    def test_manual_entries_stop_after_first_correct_patch(self):
        pending = {
            ("debugrepair", "A-1"): [
                {"method": "debugrepair", "bug_id": "A-1", "patch_index": 1, "patch_id": "debugrepair:A-1:1", "patch": "p1"},
                {"method": "debugrepair", "bug_id": "A-1", "patch_index": 2, "patch_id": "debugrepair:A-1:2", "patch": "p2"},
            ]
        }

        entries = manual_result_entries(
            pending,
            {"debugrepair:A-1:1": ("Correct", "equivalent")},
        )

        self.assertEqual([entry["patch_id"] for entry in entries], ["debugrepair:A-1:1"])
        self.assertEqual(entries[0]["evaluator_model"], "codex-manual")

    def test_result_entry_records_evaluator_boundary_without_api_key(self):
        record = {
            "method": "basic",
            "bug_id": "A-1",
            "patch_index": 1,
            "patch_id": "basic:A-1:1",
            "patch": "void f() {}",
        }

        entry = result_entry(
            record,
            judgment="Correct",
            exact_match=False,
            model="deepseek-v4-flash",
            base_url="https://www.rightapi.ai/deepseek/v1",
        )

        self.assertEqual(entry["evaluator_model"], "deepseek-v4-flash")
        self.assertEqual(entry["evaluator_base_url"], "https://www.rightapi.ai/deepseek/v1")
        self.assertNotIn("api_key", entry)

    def test_browser_compatible_headers_include_user_agent(self):
        headers = browser_compatible_headers()

        self.assertIn("Mozilla/5.0", headers["User-Agent"])
        self.assertEqual(headers["Accept"], "application/json")

    def test_builds_one_record_for_each_plausible_patch(self):
        results = {
            "A-1": {"status": "success", "plausible_patches": ["int f(){return 1;}"]},
            "A-2": {"status": "success", "plausible_patches": ["void f(){}", "void f(){ return; }"]},
            "A-3": {"status": "fail", "plausible_patches": []},
        }

        records = build_patch_records("debugrepair", results)

        self.assertEqual(
            [(r["bug_id"], r["patch_index"]) for r in records],
            [("A-1", 1), ("A-2", 1), ("A-2", 2)],
        )
        self.assertEqual(len({r["patch_id"] for r in records}), 3)

    def test_normalization_ignores_comments_and_whitespace(self):
        self.assertEqual(
            normalize_code("int f() { /* note */ return 1; // same\n}"),
            normalize_code("int f(){return 1;}"),
        )

    def test_response_parser_accepts_one_unambiguous_label(self):
        self.assertEqual(classify_response("Correct"), "Correct")
        self.assertEqual(classify_response(" Incorrect \n"), "Incorrect")
        self.assertEqual(classify_response("Correct\n```"), "Correct")
        self.assertEqual(classify_response("Correct\n\\answer{Correct}"), "Correct")
        self.assertEqual(classify_response("Not Correct"), "Unknown")
        self.assertEqual(classify_response("Correct or Incorrect"), "Unknown")

    def test_summary_counts_patches_and_unique_correct_bugs(self):
        entries = [
            {"method": "basic", "bug_id": "A-1", "judgment": "Correct"},
            {"method": "debugrepair", "bug_id": "A-1", "judgment": "Correct"},
            {"method": "debugrepair", "bug_id": "A-1", "judgment": "Incorrect"},
            {"method": "debugrepair", "bug_id": "A-2", "judgment": "Error"},
        ]

        summary = summarize_results(entries, {"basic": 1, "debugrepair": 3})

        self.assertEqual(summary["basic"]["correct_patches"], 1)
        self.assertEqual(summary["basic"]["correct_bugs"], 1)
        self.assertEqual(summary["debugrepair"]["correct_patches"], 1)
        self.assertEqual(summary["debugrepair"]["correct_bugs"], 1)
        self.assertEqual(summary["debugrepair"]["errors"], 1)

    def test_summary_uses_latest_retry_result_for_each_patch(self):
        entries = [
            {"method": "basic", "bug_id": "A-1", "patch_id": "basic:A-1:1", "judgment": "Error"},
            {"method": "basic", "bug_id": "A-1", "patch_id": "basic:A-1:1", "judgment": "Correct"},
        ]

        summary = summarize_results(entries, {"basic": 1})

        self.assertEqual(summary["basic"]["completed_patches"], 1)
        self.assertEqual(summary["basic"]["correct_patches"], 1)
        self.assertEqual(summary["basic"]["errors"], 0)

    def test_correct_bug_is_not_scheduled_again(self):
        records = [
            {"method": "debugrepair", "bug_id": "A-1", "patch_index": 1, "patch_id": "debugrepair:A-1:1"},
            {"method": "debugrepair", "bug_id": "A-1", "patch_index": 2, "patch_id": "debugrepair:A-1:2"},
            {"method": "debugrepair", "bug_id": "A-2", "patch_index": 1, "patch_id": "debugrepair:A-2:1"},
        ]
        completed = [
            {"method": "debugrepair", "bug_id": "A-1", "patch_id": "debugrepair:A-1:1", "judgment": "Correct"},
        ]

        grouped = group_pending_by_bug(records, completed)

        self.assertNotIn(("debugrepair", "A-1"), grouped)
        self.assertEqual(
            [item["patch_id"] for item in grouped[("debugrepair", "A-2")]],
            ["debugrepair:A-2:1"],
        )

    def test_error_and_unknown_results_are_retried_on_resume(self):
        records = [
            {"method": "debugrepair", "bug_id": "A-1", "patch_index": 1, "patch_id": "debugrepair:A-1:1"},
            {"method": "debugrepair", "bug_id": "A-1", "patch_index": 2, "patch_id": "debugrepair:A-1:2"},
        ]
        completed = [
            {"method": "debugrepair", "bug_id": "A-1", "patch_id": "debugrepair:A-1:1", "judgment": "Error"},
            {"method": "debugrepair", "bug_id": "A-1", "patch_id": "debugrepair:A-1:2", "judgment": "Unknown"},
        ]

        grouped = group_pending_by_bug(records, completed)

        self.assertEqual(
            [item["patch_id"] for item in grouped[("debugrepair", "A-1")]],
            ["debugrepair:A-1:1", "debugrepair:A-1:2"],
        )


if __name__ == "__main__":
    unittest.main()
