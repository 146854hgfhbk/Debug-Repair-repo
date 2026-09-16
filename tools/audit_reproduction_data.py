#!/usr/bin/env python3
"""Audit the preprocessed inputs required by the paper-aligned workflow."""

import argparse
import hashlib
import json
from pathlib import Path


REQUIRED_JSON = (
    "bug_info.json",
    "failing_test.json",
    "index_map.json",
    "file_hash.json",
)


def canonical_hash(value) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--write-report", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    metadata_dir = root / "data" / "bug_info"
    location_dir = root / "data" / "location"
    test_function_dir = root / "data" / "test_functions"

    loaded = {}
    missing_files = []
    for name in REQUIRED_JSON:
        path = metadata_dir / name
        if not path.is_file():
            missing_files.append(str(path))
            continue
        loaded[name] = json.loads(path.read_text(encoding="utf-8"))

    bug_info = loaded.get("bug_info.json", {})
    failing = loaded.get("failing_test.json", {})
    index_map = loaded.get("index_map.json", {})
    bug_ids = sorted(set(bug_info) | set(failing))

    missing_bug_metadata = [bug_id for bug_id in bug_ids if bug_id not in bug_info]
    missing_failing_metadata = [bug_id for bug_id in bug_ids if bug_id not in failing]
    missing_locations = [
        bug_id
        for bug_id in bug_ids
        if not (location_dir / f"{bug_id}.buggy.lines").is_file()
    ]

    empty_slice_bugs = []
    total_tests = 0
    nonempty_slices = 0
    for bug_id in bug_ids:
        tests = (failing.get(bug_id) or {}).get("failing_tests") or []
        total_tests += len(tests)
        usable = sum(bool((test.get("sliced_test") or "").strip()) for test in tests)
        nonempty_slices += usable
        if not usable:
            empty_slice_bugs.append(bug_id)

    report = {
        "root": str(root),
        "bug_count": len(bug_ids),
        "index_map_entries": len(index_map),
        "failing_test_records": total_tests,
        "nonempty_sliced_tests": nonempty_slices,
        "bugs_with_usable_purified_test": len(bug_ids) - len(empty_slice_bugs),
        "bugs_without_usable_purified_test": empty_slice_bugs,
        "buggy_location_files": len(list(location_dir.glob("*.buggy.lines"))),
        "fixed_location_files": len(list(location_dir.glob("*.fixed.lines"))),
        "groundtruth_files": sum(
            1
            for path in (location_dir / "groundtruth").rglob("*")
            if path.is_file()
        )
        if (location_dir / "groundtruth").is_dir()
        else 0,
        "legacy_test_function_files": len(list(test_function_dir.glob("*.java")))
        if test_function_dir.is_dir()
        else 0,
        "missing_required_files": missing_files,
        "missing_bug_metadata": missing_bug_metadata,
        "missing_failing_metadata": missing_failing_metadata,
        "missing_buggy_locations": missing_locations,
        "canonical_json_sha256": {
            name: canonical_hash(value) for name, value in loaded.items()
        },
        "runtime_policy": {
            "purified_test_fallback_allowed": False,
            "missing_slice_behavior": "explicit failure; never run the original test",
        },
    }

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(rendered + "\n", encoding="utf-8")

    required_complete = (
        not missing_files
        and not missing_bug_metadata
        and not missing_failing_metadata
        and not missing_locations
        and len(bug_ids) == 483
    )
    return 0 if required_complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
