import json
import os
from unittest import mock
from urllib.error import HTTPError, URLError

import pytest

from utils import remote_validation


def test_remote_validation_is_disabled_when_url_is_unset(monkeypatch):
    monkeypatch.delenv("DEBUGREPAIR_VALIDATOR_URL", raising=False)
    assert not remote_validation.is_remote_validation_enabled()


def test_remote_validation_is_enabled_when_url_is_set(monkeypatch):
    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_URL", "http://localhost:9001")
    assert remote_validation.is_remote_validation_enabled()


def test_request_remote_validation_sends_json_with_auth(monkeypatch):
    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_URL", "http://localhost:9001")
    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_TOKEN", "secret-token")
    monkeypatch.setenv("DEBUGREPAIR_LLM_LABEL", "exp-2026-08")

    mock_response = mock.Mock()
    mock_response.read.return_value = json.dumps(
        {"ok": True, "result": [True, ""]}
    ).encode("utf-8")
    urlopen = mock.Mock(return_value=mock_response)
    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    result = remote_validation.request_remote_validation(
        "validate_patch", "Chart-1", "public void foo() {}"
    )

    assert result == [True, ""]
    assert urlopen.call_count == 1
    request = urlopen.call_args.args[0]
    assert request.full_url == "http://localhost:9001/validate"
    assert request.get_header("Authorization") == "Bearer secret-token"
    assert request.get_header("Content-type") == "application/json"

    sent_data = json.loads(request.data.decode("utf-8"))
    assert sent_data["operation"] == "validate_patch"
    assert sent_data["bug_id"] == "Chart-1"
    assert sent_data["method"] == "public void foo() {}"
    assert sent_data["namespace"] == "exp-2026-08"


def test_request_handles_tuple_result():
    mock_response = mock.Mock()
    mock_response.read.return_value = json.dumps(
        {"ok": True, "result": [False, "Compile Fail"]}
    ).encode("utf-8")

    with mock.patch.dict(os.environ, {
        "DEBUGREPAIR_VALIDATOR_URL": "http://localhost:9001",
        "DEBUGREPAIR_VALIDATOR_TOKEN": "token123",
    }):
        with mock.patch("urllib.request.urlopen", return_value=mock_response):
            result = remote_validation.request_remote_validation(
                "validate_patch", "Lang-1", "void bar() {}"
            )

    assert result == [False, "Compile Fail"]


def test_request_handles_string_result():
    mock_response = mock.Mock()
    mock_response.read.return_value = json.dumps(
        {"ok": True, "result": "collected output"}
    ).encode("utf-8")

    with mock.patch.dict(os.environ, {
        "DEBUGREPAIR_VALIDATOR_URL": "http://localhost:9001",
        "DEBUGREPAIR_VALIDATOR_TOKEN": "token456",
    }):
        with mock.patch("urllib.request.urlopen", return_value=mock_response):
            result = remote_validation.request_remote_validation(
                "collect_output", "Time-1", "void baz() {}"
            )

    assert result == "collected output"


def test_request_raises_on_http_error():
    with mock.patch.dict(os.environ, {
        "DEBUGREPAIR_VALIDATOR_URL": "http://localhost:9001",
        "DEBUGREPAIR_VALIDATOR_TOKEN": "token789",
    }):
        error = HTTPError(
            "http://localhost:9001", 500, "Internal Server Error", {}, None
        )
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(remote_validation.RemoteValidationError) as exc_info:
                remote_validation.request_remote_validation(
                    "validate_patch", "Math-1", "void test() {}"
                )

    assert "HTTP 500" in str(exc_info.value)
    assert "token789" not in str(exc_info.value)


def test_request_raises_on_network_error():
    with mock.patch.dict(os.environ, {
        "DEBUGREPAIR_VALIDATOR_URL": "http://localhost:9001",
        "DEBUGREPAIR_VALIDATOR_TOKEN": "secret",
    }):
        with mock.patch("urllib.request.urlopen", side_effect=URLError("Connection refused")):
            with pytest.raises(remote_validation.RemoteValidationError) as exc_info:
                remote_validation.request_remote_validation(
                    "collect_output", "Closure-1", "void method() {}"
                )

    assert "Connection refused" in str(exc_info.value)
    assert "secret" not in str(exc_info.value)


def test_request_raises_on_malformed_json():
    mock_response = mock.Mock()
    mock_response.read.return_value = b"not json"

    with mock.patch.dict(os.environ, {
        "DEBUGREPAIR_VALIDATOR_URL": "http://localhost:9001",
        "DEBUGREPAIR_VALIDATOR_TOKEN": "token",
    }):
        with mock.patch("urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(remote_validation.RemoteValidationError) as exc_info:
                remote_validation.request_remote_validation(
                    "validate_patch", "Math-2", "void x() {}"
                )

    assert "malformed" in str(exc_info.value).lower()


def test_request_raises_on_worker_error():
    mock_response = mock.Mock()
    mock_response.read.return_value = json.dumps(
        {"ok": False, "error": "worker crashed"}
    ).encode("utf-8")

    with mock.patch.dict(os.environ, {
        "DEBUGREPAIR_VALIDATOR_URL": "http://localhost:9001",
        "DEBUGREPAIR_VALIDATOR_TOKEN": "token",
    }):
        with mock.patch("urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(remote_validation.RemoteValidationError) as exc_info:
                remote_validation.request_remote_validation(
                    "collect_output", "Time-2", "void y() {}"
                )

    assert "worker crashed" in str(exc_info.value)


def test_request_raises_on_missing_result_field():
    mock_response = mock.Mock()
    mock_response.read.return_value = json.dumps(
        {"ok": True}
    ).encode("utf-8")

    with mock.patch.dict(os.environ, {
        "DEBUGREPAIR_VALIDATOR_URL": "http://localhost:9001",
        "DEBUGREPAIR_VALIDATOR_TOKEN": "token",
    }):
        with mock.patch("urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(remote_validation.RemoteValidationError) as exc_info:
                remote_validation.request_remote_validation(
                    "check_instrumented_compiles", "Chart-2", "void z() {}"
                )

    assert "missing result" in str(exc_info.value).lower()


def test_request_uses_configured_timeout():
    mock_response = mock.Mock()
    mock_response.read.return_value = json.dumps(
        {"ok": True, "result": "output"}
    ).encode("utf-8")

    with mock.patch.dict(os.environ, {
        "DEBUGREPAIR_VALIDATOR_URL": "http://localhost:9001",
        "DEBUGREPAIR_VALIDATOR_TOKEN": "token",
        "DEBUGREPAIR_REMOTE_VALIDATION_TIMEOUT": "60",
    }):
        urlopen = mock.Mock(return_value=mock_response)
        with mock.patch("urllib.request.urlopen", urlopen):
            remote_validation.request_remote_validation(
                "collect_output", "Lang-2", "void method() {}"
            )

    assert urlopen.call_args.kwargs.get("timeout") == 60


def test_request_defaults_above_worker_timeout():
    mock_response = mock.Mock()
    mock_response.read.return_value = json.dumps(
        {"ok": True, "result": [True, ""]}
    ).encode("utf-8")

    with mock.patch.dict(os.environ, {
        "DEBUGREPAIR_VALIDATOR_URL": "http://localhost:9001",
        "DEBUGREPAIR_VALIDATOR_TOKEN": "token",
    }, clear=True):
        urlopen = mock.Mock(return_value=mock_response)
        with mock.patch("urllib.request.urlopen", urlopen):
            remote_validation.request_remote_validation(
                "validate_patch", "Math-3", "void fn() {}"
            )

    assert urlopen.call_args.kwargs.get("timeout") >= 1860


def test_request_requires_nonempty_token_before_network_call():
    with mock.patch.dict(os.environ, {
        "DEBUGREPAIR_VALIDATOR_URL": "http://localhost:9001",
        "DEBUGREPAIR_VALIDATOR_TOKEN": "",
    }, clear=True):
        with mock.patch("urllib.request.urlopen") as urlopen:
            with pytest.raises(remote_validation.RemoteValidationError) as exc_info:
                remote_validation.request_remote_validation(
                    "validate_patch", "Math-3", "void fn() {}"
                )

    assert "token" in str(exc_info.value).lower()
    urlopen.assert_not_called()


@pytest.mark.parametrize(
    "operation,result",
    [
        ("validate_patch", "not-a-pair"),
        ("validate_patch", [True]),
        ("validate_patch", ["yes", ""]),
        ("check_instrumented_compiles", [True, 1]),
        ("collect_output", ["not-a-string"]),
    ],
)
def test_request_rejects_invalid_operation_result_shapes(operation, result):
    response = mock.Mock()
    response.read.return_value = json.dumps(
        {"ok": True, "result": result}
    ).encode("utf-8")
    with mock.patch.dict(os.environ, {
        "DEBUGREPAIR_VALIDATOR_URL": "http://localhost:9001",
        "DEBUGREPAIR_VALIDATOR_TOKEN": "token",
    }, clear=True):
        with mock.patch("urllib.request.urlopen", return_value=response):
            with pytest.raises(remote_validation.RemoteValidationError):
                remote_validation.request_remote_validation(
                    operation, "Math-3", "void fn() {}"
                )


def test_collect_output_remote_dispatch_is_not_wrapped_by_local_timeout():
    from utils import collect_output

    assert not hasattr(collect_output.collect_output, "__wrapped__")
    assert hasattr(collect_output._collect_output_local, "__wrapped__")


def test_validate_patch_delegates_when_remote_enabled(monkeypatch):
    from utils import validate
    from defs.bug_info import BugInfo

    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_URL", "http://localhost:9001")
    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_TOKEN", "token")

    request_mock = mock.Mock(return_value=[True, ""])
    monkeypatch.setattr(
        "utils.remote_validation.request_remote_validation", request_mock
    )

    bug_info = mock.Mock(spec=BugInfo)
    result = validate.validate_patch("Chart-1", "patch code", bug_info)

    assert result == (True, "")
    assert request_mock.call_count == 1
    assert request_mock.call_args.args == ("validate_patch", "Chart-1", "patch code")


def test_validate_patch_uses_local_when_remote_disabled(monkeypatch):
    from utils import validate

    monkeypatch.delenv("DEBUGREPAIR_VALIDATOR_URL", raising=False)

    request_mock = mock.Mock()
    monkeypatch.setattr(
        "utils.remote_validation.request_remote_validation", request_mock
    )

    # Mock the local implementation to avoid actual Defects4J calls
    monkeypatch.setattr(validate, "_run_defects4j", mock.Mock())
    monkeypatch.setattr(validate, "_delete_dir", mock.Mock())
    monkeypatch.setattr(validate, "_read_source_lines", mock.Mock(return_value=[]))
    monkeypatch.setattr(validate, "_run_test", mock.Mock(return_value=(False, False, False, False, [])))

    bug_info = mock.Mock()
    bug_info.start_line = 1
    bug_info.end_line = 1

    # Should use local path, not call remote
    try:
        validate.validate_patch("Chart-1", "patch", bug_info)
    except Exception:
        pass  # Local implementation may fail, but we're testing it was called

    assert request_mock.call_count == 0


def test_check_instrumented_compiles_delegates_when_remote_enabled(monkeypatch):
    from utils import collect_output
    from defs.bug_info import BugInfo

    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_URL", "http://localhost:9001")
    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_TOKEN", "token")

    request_mock = mock.Mock(return_value=[True, ""])
    monkeypatch.setattr(
        "utils.remote_validation.request_remote_validation", request_mock
    )

    bug_info = mock.Mock(spec=BugInfo)
    result = collect_output.check_instrumented_compiles(
        "Lang-1", bug_info, "instrumented method"
    )

    assert result == (True, "")
    assert request_mock.call_count == 1
    assert request_mock.call_args.args == (
        "check_instrumented_compiles", "Lang-1", "instrumented method"
    )


def test_check_instrumented_compiles_uses_local_when_remote_disabled(monkeypatch):
    from utils import collect_output

    monkeypatch.delenv("DEBUGREPAIR_VALIDATOR_URL", raising=False)

    request_mock = mock.Mock()
    monkeypatch.setattr(
        "utils.remote_validation.request_remote_validation", request_mock
    )

    # Mock local implementation
    monkeypatch.setattr(collect_output, "_run_defects4j", mock.Mock())
    monkeypatch.setattr(collect_output, "tempfile", mock.Mock())
    monkeypatch.setattr(collect_output.shutil, "rmtree", mock.Mock())

    bug_info = mock.Mock()
    bug_info.start_line = 1
    bug_info.end_line = 5

    try:
        collect_output.check_instrumented_compiles(
            "Time-1", bug_info, "method code"
        )
    except Exception:
        pass  # Local implementation may fail

    assert request_mock.call_count == 0


def test_collect_output_delegates_when_remote_enabled(monkeypatch):
    from utils import collect_output
    from defs.bug_info import BugInfo

    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_URL", "http://localhost:9001")
    monkeypatch.setenv("DEBUGREPAIR_VALIDATOR_TOKEN", "token")

    request_mock = mock.Mock(return_value="collected output")
    monkeypatch.setattr(
        "utils.remote_validation.request_remote_validation", request_mock
    )

    bug_info = mock.Mock(spec=BugInfo)
    result = collect_output.collect_output(
        "Math-1", bug_info, "instrumented method"
    )

    assert result == "collected output"
    assert request_mock.call_count == 1
    assert request_mock.call_args.args == (
        "collect_output", "Math-1", "instrumented method"
    )


def test_collect_output_uses_local_when_remote_disabled(monkeypatch):
    from utils import collect_output

    monkeypatch.delenv("DEBUGREPAIR_VALIDATOR_URL", raising=False)

    request_mock = mock.Mock()
    monkeypatch.setattr(
        "utils.remote_validation.request_remote_validation", request_mock
    )

    # Mock local implementation to avoid timeout decorator issues
    monkeypatch.setattr(collect_output, "_run_defects4j", mock.Mock())
    monkeypatch.setattr(collect_output, "_delete_dir", mock.Mock())

    bug_info = mock.Mock()
    bug_info.failing_tests = []

    try:
        collect_output.collect_output("Closure-1", bug_info, "method")
    except Exception:
        pass  # Local implementation may fail

    assert request_mock.call_count == 0


def test_remote_validation_error_propagates_without_catch():
    """RemoteValidationError should not be caught at validate_patch."""
    from utils import validate

    with mock.patch.dict(os.environ, {
        "DEBUGREPAIR_VALIDATOR_URL": "http://localhost:9001",
        "DEBUGREPAIR_VALIDATOR_TOKEN": "token",
    }):
        mock_request = mock.Mock(
            side_effect=remote_validation.RemoteValidationError("infrastructure down")
        )
        with mock.patch(
            "utils.remote_validation.request_remote_validation", mock_request
        ):
            bug_info = mock.Mock()
            with pytest.raises(remote_validation.RemoteValidationError) as exc_info:
                validate.validate_patch("Chart-5", "patch", bug_info)

    assert "infrastructure down" in str(exc_info.value)
