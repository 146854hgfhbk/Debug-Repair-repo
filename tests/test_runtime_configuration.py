import importlib
import os
import sys
import threading
import time
from unittest import mock

import pytest


def test_repair_request_omits_reasoning_effort(monkeypatch):
    from config import InstrumentationLLMConfig, LLMConfig
    from llm.llm_client import LLMClient

    create = mock.Mock(
        return_value=mock.Mock(
            choices=[mock.Mock(message=mock.Mock(content="patch"))],
            usage=None,
        )
    )
    monkeypatch.setattr(
        "llm.llm_client.OpenAI",
        mock.Mock(return_value=mock.Mock(chat=mock.Mock(completions=mock.Mock(create=create)))),
    )
    monkeypatch.setattr(LLMConfig, "REASONING_EFFORT", "xhigh", raising=False)
    monkeypatch.setattr(LLMConfig, "TEMPERATURE", None)
    monkeypatch.setattr(InstrumentationLLMConfig, "API_KEY", "instrument-key")
    monkeypatch.setattr(InstrumentationLLMConfig, "BASE_URL", "https://instrument.example")

    LLMClient().generate_response([{"role": "user", "content": "repair"}], "test")

    assert "reasoning_effort" not in create.call_args.kwargs
    assert "temperature" not in create.call_args.kwargs


def test_openai_request_retries_transient_failures(monkeypatch):
    from config import InstrumentationLLMConfig, LLMConfig
    from llm.llm_client import LLMClient

    response = mock.Mock(
        choices=[mock.Mock(message=mock.Mock(content="patch"))],
        usage=None,
    )
    create = mock.Mock(side_effect=[RuntimeError("temporary"), response])
    client = mock.Mock(chat=mock.Mock(completions=mock.Mock(create=create)))
    monkeypatch.setattr("llm.llm_client.OpenAI", mock.Mock(return_value=client))
    monkeypatch.setattr(LLMConfig, "MAX_RETRIES", 2)
    monkeypatch.setattr(LLMConfig, "TEMPERATURE", None)
    monkeypatch.setattr(InstrumentationLLMConfig, "API_KEY", "instrument-key")
    monkeypatch.setattr(InstrumentationLLMConfig, "BASE_URL", "https://instrument.example")

    content, usage = LLMClient().generate_response(
        [{"role": "user", "content": "repair"}],
        "debug_repair",
    )

    assert content == "patch"
    assert usage == {}
    assert create.call_count == 2


def test_empty_instrumentation_reasoning_effort_is_omitted(monkeypatch):
    from config import InstrumentationLLMConfig, LLMConfig
    from llm.llm_client import LLMClient

    create = mock.Mock(
        return_value=mock.Mock(
            choices=[mock.Mock(message=mock.Mock(content="instrumented"))],
            usage=None,
        )
    )
    client = mock.Mock(chat=mock.Mock(completions=mock.Mock(create=create)))
    monkeypatch.setattr("llm.llm_client.OpenAI", mock.Mock(return_value=client))
    monkeypatch.setattr(LLMConfig, "TEMPERATURE", None)
    monkeypatch.setattr(InstrumentationLLMConfig, "API_KEY", "instrument-key")
    monkeypatch.setattr(InstrumentationLLMConfig, "BASE_URL", "https://instrument.example")
    monkeypatch.setattr(InstrumentationLLMConfig, "REASONING_EFFORT", "")
    monkeypatch.setattr(InstrumentationLLMConfig, "TEMPERATURE", None)

    LLMClient().generate_response(
        [{"role": "user", "content": "instrument"}],
        "insert_print",
    )

    assert "reasoning_effort" not in create.call_args.kwargs


def test_insert_print_uses_dedicated_instrumentation_model(monkeypatch):
    from config import InstrumentationLLMConfig, LLMConfig
    from llm.llm_client import LLMClient

    repair_create = mock.Mock(
        return_value=mock.Mock(
            choices=[mock.Mock(message=mock.Mock(content="repair"))],
            usage=None,
        )
    )
    instrumentation_create = mock.Mock(
        return_value=mock.Mock(
            choices=[mock.Mock(message=mock.Mock(content="instrumented"))],
            usage=None,
        )
    )
    openai_factory = mock.Mock(
        side_effect=[
            mock.Mock(chat=mock.Mock(completions=mock.Mock(create=repair_create))),
            mock.Mock(chat=mock.Mock(completions=mock.Mock(create=instrumentation_create))),
        ]
    )
    monkeypatch.setattr("llm.llm_client.OpenAI", openai_factory)
    monkeypatch.setattr(LLMConfig, "API_KEY", "repair-key")
    monkeypatch.setattr(LLMConfig, "BASE_URL", "https://repair.example/v1")
    monkeypatch.setattr(LLMConfig, "MODEL", "repair-model")
    monkeypatch.setattr(LLMConfig, "REASONING_EFFORT", "medium")
    monkeypatch.setattr(LLMConfig, "TEMPERATURE", None)
    monkeypatch.setattr(InstrumentationLLMConfig, "API_KEY", "instrument-key")
    monkeypatch.setattr(InstrumentationLLMConfig, "BASE_URL", "https://instrument.example")
    monkeypatch.setattr(InstrumentationLLMConfig, "MODEL", "claude-opus-5")
    monkeypatch.setattr(InstrumentationLLMConfig, "REASONING_EFFORT", "high")
    monkeypatch.setattr(InstrumentationLLMConfig, "TEMPERATURE", None)

    client = LLMClient()
    client.generate_response([{"role": "user", "content": "instrument"}], "insert_print")
    client.generate_response([{"role": "user", "content": "repair"}], "debug_repair")

    assert openai_factory.call_args_list == [
        mock.call(api_key="repair-key", base_url="https://repair.example/v1"),
        mock.call(api_key="instrument-key", base_url="https://instrument.example"),
    ]
    assert instrumentation_create.call_args.kwargs["model"] == "claude-opus-5"
    assert instrumentation_create.call_args.kwargs["reasoning_effort"] == "high"
    assert repair_create.call_args.kwargs["model"] == "repair-model"
    assert "reasoning_effort" not in repair_create.call_args.kwargs


def test_config_reads_bug_workers_from_environment(monkeypatch):
    monkeypatch.setenv("DEBUGREPAIR_BUG_WORKERS", "16")
    monkeypatch.setenv("DEBUGREPAIR_LLM_TIMEOUT", "600")
    monkeypatch.setenv("DEBUGREPAIR_DATA_ROOT", "/tmp/d4j3-data")
    monkeypatch.setenv("DEBUGREPAIR_DEFECTS4J", "/opt/defects4j-3.0")
    monkeypatch.setenv("DEBUGREPAIR_DEBUG_PATH", "/tmp/debug-preview")
    import config

    importlib.reload(config)

    assert config.BasicConfig.THREAD_COUNT == 16
    assert config.LLMConfig.TIMEOUT_LIMIT == 600
    assert config.BasicConfig.BUG_INFO_PATH == os.path.join(
        "/tmp/d4j3-data", "bug_info"
    )
    assert config.BasicConfig.LOC_PATH == os.path.join("/tmp/d4j3-data", "location")
    assert config.ValidatorConfig.DEFECTS4J_EXECUTABLE == "/opt/defects4j-3.0"
    assert config.BasicConfig.DEBUG_PATH == "/tmp/debug-preview"


def test_server_entrypoint_omits_repair_reasoning_effort(monkeypatch):
    entrypoint_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "server-entrypoint.py")
    )
    spec = importlib.util.spec_from_file_location("server_entrypoint", entrypoint_path)
    server_entrypoint = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server_entrypoint)
    from config import InstrumentationLLMConfig, LLMConfig

    settings = {
        "DEBUGREPAIR_LLM_LABEL": "composite",
        "DEBUGREPAIR_LLM_BASE_URL": "https://repair.example/v1",
        "DEBUGREPAIR_LLM_MODEL": "repair-model",
        "DEBUGREPAIR_LLM_API_KEY": "repair-key",
        "DEBUGREPAIR_INSTRUMENT_LLM_BASE_URL": "https://instrument.example/v1",
        "DEBUGREPAIR_INSTRUMENT_LLM_MODEL": "claude-opus-5",
        "DEBUGREPAIR_INSTRUMENT_LLM_API_KEY": "instrument-key",
        "DEBUGREPAIR_INSTRUMENT_LLM_REASONING_EFFORT": "high",
        "DEBUGREPAIR_INSTRUMENT_LLM_PROVIDER": "openai",
    }
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("DEBUGREPAIR_LLM_REASONING_EFFORT", raising=False)

    server_entrypoint._configure_llm()

    assert LLMConfig.REASONING_EFFORT == ""
    assert InstrumentationLLMConfig.REASONING_EFFORT == "high"


def test_server_entrypoint_defaults_to_one_paper_backbone(monkeypatch):
    entrypoint_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "server-entrypoint.py")
    )
    spec = importlib.util.spec_from_file_location("server_entrypoint", entrypoint_path)
    server_entrypoint = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server_entrypoint)
    from config import InstrumentationLLMConfig, LLMConfig

    settings = {
        "DEBUGREPAIR_LLM_LABEL": "paper-model",
        "DEBUGREPAIR_LLM_BASE_URL": "https://model.example/v1",
        "DEBUGREPAIR_LLM_MODEL": "paper-backbone",
        "DEBUGREPAIR_LLM_API_KEY": "paper-key",
    }
    for name, value in settings.items():
        monkeypatch.setenv(name, value)
    for name in (
        "DEBUGREPAIR_LLM_TEMPERATURE",
        "DEBUGREPAIR_INSTRUMENT_LLM_BASE_URL",
        "DEBUGREPAIR_INSTRUMENT_LLM_MODEL",
        "DEBUGREPAIR_INSTRUMENT_LLM_API_KEY",
        "DEBUGREPAIR_INSTRUMENT_LLM_REASONING_EFFORT",
        "DEBUGREPAIR_INSTRUMENT_LLM_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)

    server_entrypoint._configure_llm()

    assert LLMConfig.TEMPERATURE == 1.0
    assert InstrumentationLLMConfig.BASE_URL == LLMConfig.BASE_URL
    assert InstrumentationLLMConfig.MODEL == LLMConfig.MODEL
    assert InstrumentationLLMConfig.API_KEY == LLMConfig.API_KEY
    assert InstrumentationLLMConfig.REASONING_EFFORT == ""
    assert InstrumentationLLMConfig.PROVIDER == "openai"


def test_server_entrypoint_rejects_unknown_instrumentation_provider(monkeypatch):
    entrypoint_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "server-entrypoint.py")
    )
    spec = importlib.util.spec_from_file_location("server_entrypoint", entrypoint_path)
    server_entrypoint = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server_entrypoint)

    settings = {
        "DEBUGREPAIR_LLM_LABEL": "composite",
        "DEBUGREPAIR_LLM_BASE_URL": "https://repair.example/v1",
        "DEBUGREPAIR_LLM_MODEL": "repair-model",
        "DEBUGREPAIR_LLM_API_KEY": "repair-key",
        "DEBUGREPAIR_INSTRUMENT_LLM_BASE_URL": "https://instrument.example",
        "DEBUGREPAIR_INSTRUMENT_LLM_MODEL": "claude-sonnet-5",
        "DEBUGREPAIR_INSTRUMENT_LLM_API_KEY": "instrument-key",
        "DEBUGREPAIR_INSTRUMENT_LLM_REASONING_EFFORT": "max",
        "DEBUGREPAIR_INSTRUMENT_LLM_PROVIDER": "unsupported",
    }
    for name, value in settings.items():
        monkeypatch.setenv(name, value)

    with pytest.raises(SystemExit, match="Unsupported instrumentation provider"):
        server_entrypoint._configure_llm()


def test_resume_filters_only_terminal_results(tmp_path, monkeypatch):
    import runner

    output_file = tmp_path / "output_log.json"
    output_file.write_text(
        '{"Chart-1":{"status":"success"},'
        '"Chart-2":{"status":"fail"},'
        '"Chart-3":{"status":"in-progress"}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "result_file_path", lambda: str(output_file), raising=False)

    assert runner.filter_terminal_bugs(["Chart-1", "Chart-2", "Chart-3", "Chart-4"]) == [
        "Chart-3",
        "Chart-4",
    ]


def test_llm_json_log_writes_are_serialized(tmp_path, monkeypatch):
    import json
    from config import BasicConfig, LLMConfig
    from llm.llm_client import LLMClient

    monkeypatch.setattr(BasicConfig, "LOG_PATH", str(tmp_path))
    monkeypatch.setattr(BasicConfig, "DEBUG_MODE", True)
    monkeypatch.setattr(LLMConfig, "LLM_MODEL", "test-model")
    real_dump = json.dump
    active = 0
    maximum_active = 0
    state_lock = threading.Lock()

    def observed_dump(*args, **kwargs):
        nonlocal active, maximum_active
        with state_lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.01)
        try:
            return real_dump(*args, **kwargs)
        finally:
            with state_lock:
                active -= 1

    monkeypatch.setattr(json, "dump", observed_dump)
    client = object.__new__(LLMClient)
    threads = [
        threading.Thread(target=client._log_to_file, args=(str(i), [], "ok", "response"))
        for i in range(8)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert maximum_active == 1
