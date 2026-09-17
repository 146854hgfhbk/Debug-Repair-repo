import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def run(command, *, cwd=None, timeout=300):
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=os.environ.copy(),
    )


def require_success(stage, completed):
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"{stage} failed ({completed.returncode}): {detail}")


def load_slicer(path):
    spec = importlib.util.spec_from_file_location("audited_java_slicer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_triggers(output):
    triggers = []
    for line in output.splitlines():
        value = line.strip()
        if value.startswith("---"):
            value = value[3:].strip()
        if "::" in value:
            triggers.append(value)
    return triggers


def exported_dir(checkout, property_name):
    completed = run(["defects4j", "export", "-p", property_name], cwd=checkout)
    require_success(f"export {property_name}", completed)
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"empty Defects4J property: {property_name}")
    return lines[-1]


def replace_method(source, method_name, replacement, marker):
    repository_src = str(Path(__file__).resolve().parents[1] / "src")
    if repository_src not in sys.path:
        sys.path.insert(0, repository_src)
    from utils.java_rule_instrumenter import replace_method_source

    return replace_method_source(source, method_name, replacement, marker)


def read_java_source(source_file):
    source_bytes = Path(source_file).read_bytes()
    try:
        return source_bytes.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return source_bytes.decode("iso-8859-1"), "iso-8859-1"


def write_java_source(source_file, source, encoding):
    try:
        Path(source_file).write_bytes(source.encode(encoding))
        return encoding
    except UnicodeEncodeError:
        Path(source_file).write_bytes(source.encode("utf-8"))
        return "utf-8"


def restore_source_and_clean(checkout, source_file, source, encoding):
    write_java_source(source_file, source, encoding)
    run(["defects4j", "clean"], cwd=checkout, timeout=300)


def result_error(text):
    return text.startswith("错误:")


def normalized_failure_message(value):
    return " ".join((value or "").split())


def test_source_class(record):
    return (
        record.get("test_source_file_path")
        or record.get("test_file_path")
        or ""
    ).strip().replace("/", ".").replace("\\", ".")


def test_method_source(record):
    full_test = (record.get("full_test") or "").strip()
    if full_test and full_test.lower() != "source code not available":
        return record.get("full_test")
    return record.get("failing_function") or ""


def fallback_result(slicer_result, full_test):
    diagnostic = slicer_result.get("diagnostic") or slicer_result.get("sliced_method") or ""
    return {
        "status": "fallback",
        "sliced_method": full_test,
        "dependencies": {"info": diagnostic},
        "diagnostic": diagnostic,
    }


def metadata_unusable_reason(record):
    if not (record.get("test_method_name") or "").strip():
        return "missing test method"
    if not (record.get("test_file_path") or "").strip():
        return "missing test class"
    return None


def stable_failure_signature(value):
    """Normalize volatile numeric values while retaining exception/message text."""
    normalized = normalized_failure_message(value)
    normalized = re.sub(r"(?i)\b0x[0-9a-f]+\b", "<number>", normalized)
    return re.sub(
        r"(?<![A-Za-z_$])-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?",
        "<number>",
        normalized,
    )


def failure_signature_preserved(expected, observed):
    if not expected:
        return True
    return stable_failure_signature(expected) in stable_failure_signature(observed)


def apply_purification_result(record, slicer_result):
    """Persist only a validated slice or an explicit full-test fallback."""
    status = slicer_result.get("status")
    if status not in {"validated", "fallback"}:
        raise ValueError(f"refusing to persist unverified slicer status: {status}")
    record["sliced_test"] = slicer_result.get("sliced_method") or ""
    record["dependencies"] = slicer_result.get("dependencies") or {}
    record["purification_status"] = status
    record["purification_diagnostic"] = slicer_result.get("diagnostic") or ""


def write_metadata_atomically(path, metadata):
    path = Path(path)
    backup = path.with_name(f"{path.name}.backup-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(path, backup)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return backup


def audit_test(slicer, bug_id, record, audit_root, update_metadata=False):
    project, number = bug_id.split("-", 1)
    method = (record.get("test_method_name") or "").strip()
    test_class = (record.get("test_file_path") or "").strip().replace("/", ".")
    source_class = test_source_class(record)
    failing_line = (record.get("failing_line") or "").strip()
    expected_failure = normalized_failure_message(record.get("failure_message"))
    full_test = test_method_source(record)
    item = {
        "bug_id": bug_id,
        "test_class": test_class,
        "test_source_class": source_class,
        "test_method": method,
        "has_failing_line": bool(failing_line),
        "status": "pending",
    }
    unusable_reason = metadata_unusable_reason(record)
    if unusable_reason:
        item.update(status="metadata_unusable", diagnostic=unusable_reason)
        return item

    checkout = Path(tempfile.mkdtemp(prefix=f"{bug_id}-", dir=audit_root))
    started = time.monotonic()
    try:
        completed = run(
            ["defects4j", "checkout", "-p", project, "-v", f"{number}b", "-w", str(checkout)],
            timeout=300,
        )
        require_success("checkout", completed)
        triggers_result = run(["defects4j", "export", "-p", "tests.trigger"], cwd=checkout)
        require_success("export triggers", triggers_result)
        triggers = parse_triggers(triggers_result.stdout)
        selector = f"{test_class}::{method}"
        item["is_exported_trigger"] = selector in triggers

        test_dir = exported_dir(checkout, "dir.src.tests")
        test_file = checkout / test_dir / Path(*source_class.split(".")).with_suffix(".java")
        item["test_file_exists"] = test_file.is_file()
        if not test_file.is_file():
            item.update(status="test_file_missing", diagnostic=str(test_file.relative_to(checkout)))
            return item

        source, source_encoding = read_java_source(test_file)
        source_encoding_box = [source_encoding]

        def validate_candidate(candidate, dependencies):
            patched_candidate = replace_method(
                source, method, candidate, "JAVA_SLICER_VALIDATION_MARKER"
            )
            source_encoding_box[0] = write_java_source(
                test_file, patched_candidate, source_encoding_box[0]
            )
            try:
                compile_result = run(
                    ["defects4j", "compile"], cwd=checkout, timeout=300
                )
                if compile_result.returncode:
                    return {
                        "accepted": False,
                        "diagnostic": "candidate did not compile",
                    }
                test_result = run(
                    ["defects4j", "test", "-t", selector],
                    cwd=checkout,
                    timeout=300,
                )
                failing_tests_path = checkout / "failing_tests"
                failing_tests = (
                    failing_tests_path.read_text(encoding="utf-8", errors="replace")
                    if failing_tests_path.is_file()
                    else ""
                )
                observed = selector in failing_tests
                signature_preserved = failure_signature_preserved(
                    expected_failure, failing_tests
                )
                return {
                    "accepted": observed and signature_preserved,
                    "diagnostic": (
                        "candidate compiled and preserved the trigger failure"
                        if observed and signature_preserved else
                        "candidate compiled but did not preserve the stable trigger failure"
                    ),
                    "test_returncode": test_result.returncode,
                }
            finally:
                restore_source_and_clean(
                    checkout, test_file, source, source_encoding_box[0]
                )

        results = slicer.analyze_test_with_dependencies(
            method, full_test, failing_line, str(test_file),
            validator=validate_candidate,
        )
        if len(results) != 1:
            raise RuntimeError(f"expected one slicer result, got {len(results)}")
        if results[0].get("status") == "error" and full_test.strip():
            results[0] = fallback_result(results[0], full_test)
        sliced = results[0].get("sliced_method") or ""
        dependencies = results[0].get("dependencies") or {}
        item["original_chars"] = len(full_test)
        item["sliced_chars"] = len(sliced)
        item["dependency_methods"] = len(dependencies.get("methods") or [])
        item["dependency_variables"] = len(dependencies.get("variables") or [])
        item["slicer_info"] = dependencies.get("info")
        item["slicer_status"] = results[0].get("status")
        item["slicer_diagnostic"] = results[0].get("diagnostic")
        if not sliced.strip() or result_error(sliced):
            item.update(status="slicer_error", diagnostic=sliced[:1000])
            return item
        if dependencies.get("info") and results[0].get("status") != "fallback":
            item.update(status="unsliced_fallback", diagnostic=dependencies["info"])
            return item

        patched = replace_method(
            source,
            method,
            sliced,
            "JAVA_SLICER_AUDIT_MARKER",
        )
        source_encoding_box[0] = write_java_source(
            test_file, patched, source_encoding_box[0]
        )
        compile_result = run(["defects4j", "compile"], cwd=checkout, timeout=300)
        item["compile_returncode"] = compile_result.returncode
        if compile_result.returncode:
            item.update(
                status="compile_failed",
                diagnostic=(compile_result.stderr or compile_result.stdout).strip()[-4000:],
            )
            return item

        test_result = run(
            ["defects4j", "test", "-t", selector], cwd=checkout, timeout=300
        )
        combined = "\n".join(x for x in (test_result.stdout, test_result.stderr) if x)
        failing_tests_path = checkout / "failing_tests"
        failing_tests = (
            failing_tests_path.read_text(encoding="utf-8", errors="replace")
            if failing_tests_path.is_file()
            else ""
        )
        item["test_returncode"] = test_result.returncode
        item["failing_tests_file"] = failing_tests_path.is_file()
        item["failure_observed"] = selector in failing_tests
        item["expected_failure_message"] = expected_failure
        item["failure_message_preserved"] = (
            failure_signature_preserved(expected_failure, failing_tests)
        )
        item["failing_tests_excerpt"] = failing_tests[-1500:]
        item["output_excerpt"] = combined[-1500:]
        if not item["failure_observed"]:
            item["status"] = "failure_not_reproduced"
        elif expected_failure and not item["failure_message_preserved"]:
            item["status"] = "failure_signature_changed"
        else:
            item["status"] = "passed"
        if item["status"] == "passed" and update_metadata:
            apply_purification_result(record, results[0])
            item["metadata_updated"] = True
        return item
    except subprocess.TimeoutExpired as exc:
        item.update(status="timeout", diagnostic=f"{exc.cmd}: {exc.timeout}s")
        return item
    except Exception as exc:
        item.update(status="audit_error", diagnostic=f"{type(exc).__name__}: {exc}")
        return item
    finally:
        item["elapsed_seconds"] = round(time.monotonic() - started, 3)
        shutil.rmtree(checkout, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slicer", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--bugs", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--update-metadata",
        action="store_true",
        help="Back up and atomically update validated sliced_test records.",
    )
    args = parser.parse_args()

    slicer_path = Path(args.slicer).resolve()
    metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8"))
    slicer = load_slicer(slicer_path)
    audit_root = Path(tempfile.mkdtemp(prefix="java-slicer-d4j-audit-"))
    report = {
        "slicer_path": str(slicer_path),
        "slicer_sha256": hashlib.sha256(slicer_path.read_bytes()).hexdigest(),
        "defects4j_commit": run(
            ["git", "-C", os.environ["DEFECTS4J_HOME"], "rev-parse", "HEAD"]
        ).stdout.strip(),
        "results": [],
    }
    try:
        for bug_id in args.bugs:
            tests = (metadata.get(bug_id) or {}).get("failing_tests") or []
            if not tests:
                report["results"].append(
                    {"bug_id": bug_id, "status": "metadata_unusable", "diagnostic": "no failing tests"}
                )
                continue
            for record in tests:
                result = audit_test(
                    slicer, bug_id, record, audit_root,
                    update_metadata=args.update_metadata,
                )
                report["results"].append(result)
                print(json.dumps(result, ensure_ascii=True), flush=True)
    finally:
        shutil.rmtree(audit_root, ignore_errors=True)

    counts = {}
    for result in report["results"]:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    report["status_counts"] = counts
    Path(args.output).write_text(
        json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    if args.update_metadata:
        backup = write_metadata_atomically(Path(args.metadata), metadata)
        report["metadata_backup"] = str(backup)
        Path(args.output).write_text(
            json.dumps(report, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"status_counts": counts}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
