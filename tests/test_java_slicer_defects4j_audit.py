import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


AUDIT_PATH = Path(__file__).resolve().parents[1] / "tools" / "java_slicer_defects4j_audit.py"
SPEC = importlib.util.spec_from_file_location("java_slicer_audit", AUDIT_PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def test_persists_validated_slice():
    record = {}
    AUDIT.apply_purification_result(
        record,
        {
            "status": "validated",
            "sliced_method": "void target() {}",
            "dependencies": {"methods": [], "variables": []},
            "diagnostic": "failure preserved",
        },
    )
    assert record["sliced_test"] == "void target() {}"
    assert record["purification_status"] == "validated"


def test_persists_explicit_full_test_fallback():
    record = {}
    AUDIT.apply_purification_result(
        record,
        {
            "status": "fallback",
            "sliced_method": "void target() { original(); }",
            "dependencies": {"info": "candidate rejected"},
            "diagnostic": "candidate rejected",
        },
    )
    assert "original" in record["sliced_test"]
    assert record["purification_status"] == "fallback"


@pytest.mark.parametrize("status", ["success", "error", None])
def test_rejects_unverified_result(status):
    with pytest.raises(ValueError, match="unverified"):
        AUDIT.apply_purification_result({}, {"status": status})


def test_atomic_metadata_write_creates_backup(tmp_path):
    metadata_path = tmp_path / "failing_test.json"
    metadata_path.write_text('{"before": true}\n', encoding="utf-8")

    backup = AUDIT.write_metadata_atomically(metadata_path, {"after": True})

    assert json.loads(metadata_path.read_text(encoding="utf-8")) == {"after": True}
    assert json.loads(backup.read_text(encoding="utf-8")) == {"before": True}


def test_inherited_test_uses_declaring_source_class():
    record = {
        "test_file_path": "org.apache.commons.cli.BasicParserTest",
        "test_source_file_path": "org.apache.commons.cli.ParserTestCase",
    }

    assert AUDIT.test_source_class(record) == "org.apache.commons.cli.ParserTestCase"


def test_missing_failing_line_can_fall_back_to_full_test():
    record = {
        "test_method_name": "testWithoutKnownFailingLine",
        "test_file_path": "example.ExampleTest",
        "failing_line": None,
    }

    assert AUDIT.metadata_unusable_reason(record) is None


def test_standalone_replace_method_finds_repository_src(tmp_path):
    program = f"""
import importlib.util
spec = importlib.util.spec_from_file_location("audit", {str(AUDIT_PATH)!r})
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
source = "class T {{ void target() {{ oldCall(); }} }}"
replacement = "void target() {{ newCall(); }}"
print(audit.replace_method(source, "target", replacement, "AUDIT_MARKER"))
"""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)

    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr
    assert "newCall" in completed.stdout


def test_java_source_encoding_is_preserved_for_legacy_latin1(tmp_path):
    source_path = tmp_path / "LegacyTest.java"
    original = "class LegacyTest { String value = \"caf\N{LATIN SMALL LETTER E WITH ACUTE}\"; }"
    source_path.write_bytes(original.encode("iso-8859-1"))

    source, encoding = AUDIT.read_java_source(source_path)
    AUDIT.write_java_source(source_path, source, encoding)

    assert encoding == "iso-8859-1"
    assert source_path.read_bytes() == original.encode("iso-8859-1")


def test_java_source_write_falls_back_to_utf8_when_text_exceeds_legacy_encoding(tmp_path):
    source_path = tmp_path / "LegacyTest.java"
    source_path.write_bytes(b'class LegacyTest { String value = "caf\\xe9"; }')

    source, encoding = AUDIT.read_java_source(source_path)
    chosen = AUDIT.write_java_source(source_path, source + " // \N{CJK UNIFIED IDEOGRAPH-6D4B}", encoding)

    assert chosen == "utf-8"
    assert "\u6d4b" in source_path.read_text(encoding="utf-8")


def test_unavailable_full_test_uses_failing_function():
    record = {
        "full_test": "Source code not available",
        "failing_function": "void realTest() { assertTrue(true); }",
    }

    assert AUDIT.test_method_source(record) == record["failing_function"]


def test_slicer_error_can_be_converted_to_full_test_fallback():
    fallback = AUDIT.fallback_result(
        {"status": "error", "diagnostic": "method is ambiguous"},
        "void realTest() { assertTrue(true); }",
    )

    assert fallback["status"] == "fallback"
    assert fallback["sliced_method"].startswith("void realTest")
