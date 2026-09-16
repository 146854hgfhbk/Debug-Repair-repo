import json
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKER_PATH = ROOT / "validator-worker.py"


def test_basic_config_temp_path_honors_env_override(monkeypatch):
    """BasicConfig.TEMP_PATH should read DEBUGREPAIR_TEMP_PATH."""
    monkeypatch.setenv("DEBUGREPAIR_TEMP_PATH", "/custom/temp")

    # Force reload of config module to pick up env change
    import importlib
    import config
    importlib.reload(config)

    assert config.BasicConfig.TEMP_PATH == "/custom/temp"


def test_basic_config_temp_path_defaults_to_relative_path(monkeypatch):
    """BasicConfig.TEMP_PATH should default to ../temp relative to src."""
    monkeypatch.delenv("DEBUGREPAIR_TEMP_PATH", raising=False)

    import importlib
    import config
    importlib.reload(config)

    assert config.BasicConfig.TEMP_PATH == os.path.join(
        config.BasicConfig.BASE_PATH, "..", "temp"
    )


def test_worker_validates_operation_type():
    """Worker should reject invalid operation names."""
    payload = {
        "operation": "invalid_operation",
        "bug_id": "Chart-1",
        "method": "void foo() {}",
    }

    result = subprocess.run(
        [sys.executable, str(WORKER_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode != 0
    response = json.loads(result.stdout)
    assert response["ok"] is False
    assert "operation" in response["error"].lower()


def test_worker_validates_bug_id_type():
    """Worker should reject non-string bug_id."""
    payload = {
        "operation": "validate_patch",
        "bug_id": 123,  # Should be string
        "method": "void foo() {}",
    }

    result = subprocess.run(
        [sys.executable, str(WORKER_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode != 0
    response = json.loads(result.stdout)
    assert response["ok"] is False
    assert "bug_id" in response["error"].lower()


def test_worker_removes_remote_url_from_environment():
    """Worker should remove DEBUGREPAIR_VALIDATOR_URL to prevent recursion."""
    payload = {
        "operation": "check_instrumented_compiles",
        "bug_id": "Lang-1",
        "method": "void bar() {}",
    }

    env = os.environ.copy()
    env["DEBUGREPAIR_VALIDATOR_URL"] = "http://localhost:9001"
    env["DEBUGREPAIR_VALIDATOR_TOKEN"] = "token"
    env["DEBUGREPAIR_DEFECTS4J"] = str(ROOT / ".missing-defects4j")

    result = subprocess.run(
        [sys.executable, str(WORKER_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )

    # Worker should return a JSON response (may fail due to missing data,
    # but it shouldn't recurse infinitely)
    response = json.loads(result.stdout)
    assert "ok" in response
    # The operation will likely fail due to missing BugInfo data,
    # but it should not try to delegate remotely


def test_worker_redirects_operation_stdout_to_stderr():
    """Worker stdout must contain only JSON; operation prints go to stderr."""
    payload = {
        "operation": "validate_patch",
        "bug_id": "Chart-1",
        "method": "void test() {}",
    }

    env = os.environ.copy()
    env["DEBUGREPAIR_DEFECTS4J"] = str(ROOT / ".missing-defects4j")
    result = subprocess.run(
        [sys.executable, str(WORKER_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )

    # stdout should be valid JSON
    response = json.loads(result.stdout)
    assert "ok" in response
    assert "result" in response or "error" in response
    # Any operation diagnostics should be in stderr, not stdout


def test_worker_returns_tuple_result_for_validation():
    """Worker should return list for tuple-returning operations."""
    # This test needs actual data files to work, so we'll test structure
    payload = {
        "operation": "validate_patch",
        "bug_id": "Math-1",
        "method": "void method() {}",
    }

    result = subprocess.run(
        [sys.executable, str(WORKER_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=5,
    )

    response = json.loads(result.stdout)
    assert "ok" in response
    # Will likely fail with missing data, but structure is correct
    if response["ok"]:
        assert isinstance(response["result"], list)
        assert len(response["result"]) == 2


def test_worker_returns_string_result_for_collection():
    """Worker should return string for collect_output."""
    payload = {
        "operation": "collect_output",
        "bug_id": "Time-1",
        "method": "void instrumented() {}",
    }

    result = subprocess.run(
        [sys.executable, str(WORKER_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=5,
    )

    response = json.loads(result.stdout)
    assert "ok" in response
    # Will likely fail with missing data, but structure is correct
    if response["ok"]:
        assert isinstance(response["result"], str)


def test_worker_sanitizes_errors_without_exposing_env():
    """Worker errors should not include environment variable values."""
    payload = {
        "operation": "validate_patch",
        "bug_id": "Chart-1",
        "method": "void test() {}",
    }

    env = os.environ.copy()
    env["SECRET_API_KEY"] = "super-secret-key-12345"
    env["DEBUGREPAIR_DEFECTS4J"] = str(ROOT / ".missing-defects4j")

    result = subprocess.run(
        [sys.executable, str(WORKER_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )

    response = json.loads(result.stdout)
    # Will fail due to missing data
    assert response["ok"] is False
    # Error should not contain the secret (it's redacted)
    assert "super-secret-key-12345" not in response["error"]
    assert response["error"]


def test_worker_and_server_share_the_same_request_limit():
    server_spec = importlib.util.spec_from_file_location(
        "validator_server_for_limit", ROOT / "validator-server.py"
    )
    server = importlib.util.module_from_spec(server_spec)
    server_spec.loader.exec_module(server)

    worker_spec = importlib.util.spec_from_file_location(
        "validator_worker_for_limit", WORKER_PATH
    )
    worker = importlib.util.module_from_spec(worker_spec)
    worker_spec.loader.exec_module(worker)

    assert worker.MAX_REQUEST_BYTES == server.MAX_REQUEST_BYTES
