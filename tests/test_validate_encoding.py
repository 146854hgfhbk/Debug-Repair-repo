import os
import signal
import subprocess
from unittest import mock

import pytest

from utils import validate
from utils.validate import _read_source_lines, _run_defects4j, _stderr_path


def test_read_source_lines_falls_back_to_iso_8859_1_without_changing_path(tmp_path):
    source_path = tmp_path / "Entities.java"
    source_path.write_bytes("class Entities { // \u00a9\n}\n".encode("ISO-8859-1"))

    assert _read_source_lines(str(source_path)) == [
        "class Entities { // \u00a9",
        "}",
        "",
    ]


def test_validator_uses_configured_defects4j(monkeypatch):
    monkeypatch.setattr(
        "utils.validate.ValidatorConfig.DEFECTS4J_EXECUTABLE",
        "/opt/defects4j-3.0",
    )
    process = mock.Mock(pid=123, returncode=0)
    process.communicate.return_value = ("", "")
    popen = mock.Mock(return_value=process)
    monkeypatch.setattr("utils.validate.subprocess.Popen", popen)

    completed = _run_defects4j(["test", "-w", "/tmp/checkout"])

    assert popen.call_args.args[0][0] == "/opt/defects4j-3.0"
    assert popen.call_args.kwargs["start_new_session"] is True
    assert completed.returncode == 0


def test_linux_timeout_terminates_the_process_group(monkeypatch):
    terminate = getattr(validate, "_terminate_process_group", None)
    assert terminate is not None, "validator needs process-group timeout cleanup"

    process = mock.Mock(pid=321)
    process.poll.return_value = None
    killpg = mock.Mock(
        side_effect=[None, ProcessLookupError()]
    )
    monkeypatch.setattr(validate, "PLATFORM", "linux")
    monkeypatch.setattr(validate.os, "getpgid", mock.Mock(return_value=321), raising=False)
    monkeypatch.setattr(validate.os, "killpg", killpg, raising=False)

    terminate(process, grace_seconds=0)

    assert killpg.call_args_list == [
        mock.call(321, signal.SIGTERM),
        mock.call(321, 0),
    ]
    process.wait.assert_called()


def test_linux_timeout_escalates_when_process_group_survives(monkeypatch):
    terminate = getattr(validate, "_terminate_process_group", None)
    assert terminate is not None, "validator needs process-group timeout cleanup"

    process = mock.Mock(pid=654)
    process.poll.return_value = None
    killpg = mock.Mock()
    monkeypatch.setattr(validate, "PLATFORM", "linux")
    monkeypatch.setattr(validate.os, "getpgid", mock.Mock(return_value=654), raising=False)
    monkeypatch.setattr(validate.os, "killpg", killpg, raising=False)

    terminate(process, grace_seconds=0)

    assert killpg.call_args_list == [
        mock.call(654, signal.SIGTERM),
        mock.call(654, 0),
        mock.call(654, validate.PROCESS_KILL_SIGNAL),
    ]
    process.wait.assert_called()


def test_timeout_cleanup_does_not_signal_an_exited_process(monkeypatch):
    terminate = getattr(validate, "_terminate_process_group", None)
    assert terminate is not None, "validator needs process-group timeout cleanup"

    process = mock.Mock(pid=987)
    process.poll.return_value = 0
    killpg = mock.Mock(side_effect=ProcessLookupError())
    monkeypatch.setattr(validate, "PLATFORM", "linux")
    monkeypatch.setattr(validate.os, "killpg", killpg, raising=False)

    terminate(process, grace_seconds=0)

    assert killpg.call_args_list == [mock.call(987, 0)]
    process.wait.assert_called_once_with()


def test_timeout_cleanup_kills_surviving_group_after_leader_exits(monkeypatch):
    terminate = getattr(validate, "_terminate_process_group", None)
    assert terminate is not None, "validator needs process-group timeout cleanup"

    process = mock.Mock(pid=852)
    process.poll.return_value = 0
    killpg = mock.Mock()
    monkeypatch.setattr(validate, "PLATFORM", "linux")
    monkeypatch.setattr(validate.os, "killpg", killpg, raising=False)

    terminate(process, grace_seconds=0)

    assert killpg.call_args_list == [
        mock.call(852, 0),
        mock.call(852, signal.SIGTERM),
        mock.call(852, 0),
        mock.call(852, validate.PROCESS_KILL_SIGNAL),
    ]
    process.wait.assert_called()


def test_run_defects4j_cleans_process_group_before_propagating_timeout(monkeypatch):
    terminate = getattr(validate, "_terminate_process_group", None)
    assert terminate is not None, "validator needs process-group timeout cleanup"

    process = mock.Mock(pid=741)
    process.communicate.side_effect = subprocess.TimeoutExpired("defects4j", 10)
    monkeypatch.setattr(validate.subprocess, "Popen", mock.Mock(return_value=process))
    cleanup = mock.Mock()
    monkeypatch.setattr(validate, "_terminate_process_group", cleanup)

    with pytest.raises(subprocess.TimeoutExpired):
        _run_defects4j(["checkout", "-p", "Chart", "-v", "1b"])

    cleanup.assert_called_once_with(process)


def test_validator_stderr_is_scoped_to_checkout():
    assert _stderr_path("/tmp/experiment/test_Chart-1") == os.path.join(
        "/tmp/experiment/test_Chart-1", "stderr.txt"
    )
