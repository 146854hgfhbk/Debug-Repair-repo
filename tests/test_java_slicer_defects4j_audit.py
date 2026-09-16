import importlib.util
import json
from pathlib import Path

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
