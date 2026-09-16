import contextlib
import importlib.util
import json
import os
import sys
import threading
import time
from http.client import HTTPConnection
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "validator-server.py"


def _load_server_module():
    spec = importlib.util.spec_from_file_location("validator_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR_SERVER = _load_server_module()


@contextlib.contextmanager
def _running_server(monkeypatch, tmp_path, **handler_overrides):
    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_TOKEN", "test-token")
    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_WORK_ROOT", str(tmp_path / "work"))
    handler = VALIDATOR_SERVER.create_handler()
    for name, value in handler_overrides.items():
        setattr(handler, name, value)
    server = VALIDATOR_SERVER.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _request(address, method="POST", path="/validate", body=b"{}", headers=None):
    connection = HTTPConnection(*address, timeout=5)
    request_headers = {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json",
    }
    request_headers.update(headers or {})
    connection.request(method, path, body=body, headers=request_headers)
    response = connection.getresponse()
    payload = response.read()
    connection.close()
    return response.status, payload


def _write_worker(tmp_path, source):
    path = tmp_path / "fake-worker.py"
    path.write_text(source, encoding="utf-8")
    return str(path)


def _valid_request(operation="collect_output"):
    return json.dumps(
        {
            "operation": operation,
            "bug_id": "Chart-1",
            "method": "void method() {}",
            "namespace": "test-run",
        }
    ).encode("utf-8")


def test_server_health_endpoint_returns_ok(monkeypatch, tmp_path):
    with _running_server(monkeypatch, tmp_path) as address:
        status, payload = _request(address, method="GET", path="/health", body=None)

    assert status == 200
    assert json.loads(payload) == {"status": "ok"}


def test_server_requires_bearer_token(monkeypatch, tmp_path):
    with _running_server(monkeypatch, tmp_path) as address:
        status, _ = _request(address, headers={"Authorization": ""})
    assert status == 401


def test_server_rejects_wrong_token_using_constant_time_comparison(
    monkeypatch, tmp_path
):
    comparison = mock.Mock(return_value=False)
    hmac_module = SimpleNamespace(compare_digest=comparison)
    monkeypatch.setattr(VALIDATOR_SERVER, "hmac", hmac_module, raising=False)

    with _running_server(monkeypatch, tmp_path) as address:
        status, _ = _request(
            address,
            headers={"Authorization": "Bearer wrong-token"},
        )

    assert status == 403
    comparison.assert_called_once_with("wrong-token", "test-token")


@pytest.mark.parametrize("content_length", ["missing", "-1", "not-a-number"])
def test_server_rejects_missing_or_invalid_content_length(
    monkeypatch, tmp_path, content_length
):
    with _running_server(monkeypatch, tmp_path) as address:
        connection = HTTPConnection(*address, timeout=5)
        connection.putrequest("POST", "/validate")
        connection.putheader("Authorization", "Bearer test-token")
        connection.putheader("Content-Type", "application/json")
        if content_length != "missing":
            connection.putheader("Content-Length", content_length)
        connection.endheaders()
        response = connection.getresponse()
        response.read()
        status = response.status
        connection.close()

    assert status == 400


def test_server_validates_request_size(monkeypatch, tmp_path):
    with _running_server(monkeypatch, tmp_path, max_request_bytes=8) as address:
        status, _ = _request(address, body=b"{}        x")
    assert status == 413


def test_server_validates_content_type(monkeypatch, tmp_path):
    with _running_server(monkeypatch, tmp_path) as address:
        status, _ = _request(
            address,
            body=b"{}",
            headers={"Content-Type": "text/plain"},
        )
    assert status == 415


@pytest.mark.parametrize(
    "path,body",
    [
        ("/wrong", _valid_request()),
        ("/validate", b"[]"),
        ("/validate", json.dumps({"operation": "unknown", "bug_id": "Chart-1", "method": "x"}).encode()),
        ("/validate", json.dumps({"operation": "collect_output", "bug_id": 1, "method": "x"}).encode()),
        ("/validate", json.dumps({"operation": "collect_output", "bug_id": "Chart-1", "method": "x", "namespace": 1}).encode()),
    ],
)
def test_server_rejects_wrong_path_and_invalid_request_types(
    monkeypatch, tmp_path, path, body
):
    with _running_server(monkeypatch, tmp_path) as address:
        status, _ = _request(address, path=path, body=body)
    assert status in {400, 404}


def test_server_creates_unique_roots_and_sanitizes_worker_environment(
    monkeypatch, tmp_path
):
    worker = _write_worker(
        tmp_path,
        """import json, os, sys
json.load(sys.stdin)
result = {
    'temp': os.environ['DEBUGREPAIR_TEMP_PATH'],
    'debug': os.environ['DEBUGREPAIR_DEBUG_PATH'],
    'remote_url': os.environ.get('DEBUGREPAIR_VALIDATOR_URL'),
    'token': os.environ.get('DEBUGREPAIR_VALIDATOR_TOKEN'),
}
print(json.dumps({'ok': True, 'result': json.dumps(result)}))
""",
    )
    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_URL", "http://old-tunnel")

    with _running_server(monkeypatch, tmp_path, worker_script=worker) as address:
        responses = []
        for _ in range(2):
            status, payload = _request(address, body=_valid_request())
            assert status == 200
            responses.append(json.loads(json.loads(payload)["result"]))

    first_root = Path(responses[0]["temp"]).parent
    second_root = Path(responses[1]["temp"]).parent
    assert first_root != second_root
    assert first_root.parent == tmp_path / "work"
    assert second_root.parent == tmp_path / "work"
    assert responses[0]["remote_url"] is None
    assert responses[0]["token"] is None
    assert not first_root.exists()
    assert not second_root.exists()


def test_server_enforces_concurrency_limit(monkeypatch, tmp_path):
    active = 0
    peak = 0
    lock = threading.Lock()

    def controlled_validation(self, request_data):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.1)
        with lock:
            active -= 1
        return {"ok": True, "result": "trace"}

    monkeypatch.setattr(
        VALIDATOR_SERVER.ValidationHandler,
        "_handle_validation",
        controlled_validation,
    )
    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_WORKERS", "1")

    with _running_server(monkeypatch, tmp_path) as address:
        threads = [
            threading.Thread(target=_request, args=(address,), kwargs={"body": _valid_request()})
            for _ in range(3)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert peak == 1


def test_server_reaps_worker_after_timeout(monkeypatch):
    process = mock.Mock()
    process.pid = 1234
    process.poll.return_value = None
    process.wait.side_effect = [None]
    monkeypatch.setattr(VALIDATOR_SERVER.sys, "platform", "linux")
    monkeypatch.setattr(VALIDATOR_SERVER.os, "killpg", mock.Mock(), raising=False)
    monkeypatch.setattr(VALIDATOR_SERVER.time, "sleep", mock.Mock())

    VALIDATOR_SERVER.ValidationHandler._terminate_worker_group(object(), process)

    process.wait.assert_called()


@pytest.mark.parametrize(
    "worker_source",
    [
        "import sys; print('not-json')",
        "import json, sys; print(json.dumps([]))",
        "import json, sys; print(json.dumps({'ok': 'yes', 'result': 'trace'}))",
        "import json, sys; print(json.dumps({'ok': True, 'result': [True, 'wrong-shape']}))",
        "import json, sys; print(json.dumps({'ok': False, 'error': 7})); sys.exit(1)",
        "import json, sys; print(json.dumps({'ok': True, 'result': 'trace'})); sys.exit(1)",
    ],
)
def test_server_rejects_malformed_or_inconsistent_worker_response(
    monkeypatch, tmp_path, worker_source
):
    worker = _write_worker(tmp_path, worker_source)
    with _running_server(monkeypatch, tmp_path, worker_script=worker) as address:
        status, payload = _request(address, body=_valid_request())

    assert status == 500
    response = json.loads(payload)
    assert response["ok"] is False


def test_server_sanitizes_worker_errors(monkeypatch, tmp_path):
    worker = _write_worker(
        tmp_path,
        "import json, sys; print(json.dumps({'ok': False, 'error': 'test-token leaked'})); sys.exit(1)",
    )
    with _running_server(monkeypatch, tmp_path, worker_script=worker) as address:
        status, payload = _request(address, body=_valid_request())

    assert status == 200
    assert b"test-token" not in payload
    assert json.loads(payload)["ok"] is False


@pytest.mark.parametrize(
    "variable,value",
    [
        ("DEBUGREPAIR_VALIDATOR_WORKERS", "0"),
        ("DEBUGREPAIR_VALIDATOR_WORKERS", "not-an-int"),
        ("DEBUGREPAIR_VALIDATOR_TIMEOUT", "0"),
    ],
)
def test_server_rejects_invalid_positive_integer_configuration(
    monkeypatch, tmp_path, variable, value
):
    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_TOKEN", "test-token")
    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv(variable, value)

    with pytest.raises(ValueError):
        VALIDATOR_SERVER.create_handler()
