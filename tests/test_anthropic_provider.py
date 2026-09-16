import os
import subprocess
import sys
from unittest import mock

import pytest


def test_provider_defaults_to_openai(monkeypatch):
    """Default provider should be openai for backward compatibility"""
    env = os.environ.copy()
    env.pop("DEBUGREPAIR_INSTRUMENT_LLM_PROVIDER", None)
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
    env["PYTHONPATH"] = os.pathsep.join(
        path for path in (src_path, env.get("PYTHONPATH", "")) if path
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from config import InstrumentationLLMConfig; "
            "print(InstrumentationLLMConfig.PROVIDER)",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.stdout.strip() == "openai"


def test_anthropic_provider_constructs_native_client(monkeypatch):
    """When provider=anthropic, should construct Anthropic client"""
    from config import InstrumentationLLMConfig, LLMConfig
    from llm.llm_client import LLMClient

    openai_factory = mock.Mock(
        return_value=mock.Mock(chat=mock.Mock(completions=mock.Mock(create=mock.Mock(
            return_value=mock.Mock(choices=[mock.Mock(message=mock.Mock(content="repair"))], usage=None)
        ))))
    )
    anthropic_factory = mock.Mock(
        return_value=mock.Mock(messages=mock.Mock(create=mock.Mock(
            return_value=mock.Mock(content=[{"type": "text", "text": "instrumented"}], usage={"input_tokens": 10, "output_tokens": 20})
        )))
    )

    monkeypatch.setattr("llm.llm_client.OpenAI", openai_factory)
    monkeypatch.setattr("llm.anthropic_instrumentation_client.Anthropic", anthropic_factory)
    monkeypatch.setattr(LLMConfig, "API_KEY", "repair-key")
    monkeypatch.setattr(LLMConfig, "BASE_URL", "https://repair.example/v1")
    monkeypatch.setattr(LLMConfig, "MODEL", "repair-model")
    monkeypatch.setattr(LLMConfig, "TEMPERATURE", None)
    monkeypatch.setattr(InstrumentationLLMConfig, "PROVIDER", "anthropic")
    monkeypatch.setattr(InstrumentationLLMConfig, "API_KEY", "instrument-key")
    monkeypatch.setattr(InstrumentationLLMConfig, "BASE_URL", "https://instrument.example")
    monkeypatch.setattr(InstrumentationLLMConfig, "MODEL", "claude-sonnet-5")
    monkeypatch.setattr(InstrumentationLLMConfig, "REASONING_EFFORT", "max")
    monkeypatch.setattr(InstrumentationLLMConfig, "TEMPERATURE", None)

    client = LLMClient()
    assert openai_factory.call_count == 1
    assert anthropic_factory.call_count == 1


def test_anthropic_adapter_maps_request_response_and_usage(monkeypatch):
    from llm.anthropic_instrumentation_client import AnthropicInstrumentationClient

    create = mock.Mock(
        return_value=mock.Mock(
            content=[
                {"type": "thinking", "thinking": "hidden"},
                {"type": "text", "text": "first"},
                mock.Mock(type="text", text=" second"),
            ],
            usage={"input_tokens": 17, "output_tokens": 5},
        )
    )
    anthropic_factory = mock.Mock(
        return_value=mock.Mock(messages=mock.Mock(create=create))
    )
    monkeypatch.setattr(
        "llm.anthropic_instrumentation_client.Anthropic", anthropic_factory
    )

    client = AnthropicInstrumentationClient(
        api_key="instrument-key",
        base_url="https://instrument.example",
        timeout=600,
    )
    content, usage = client.generate_response(
        messages=[
            {"role": "system", "content": "stable system"},
            {"role": "user", "content": "instrument"},
            {"role": "assistant", "content": "prior answer"},
        ],
        model="claude-sonnet-5",
        max_tokens=4096,
        effort="max",
        temperature=None,
    )

    anthropic_factory.assert_called_once_with(
        api_key="instrument-key",
        base_url="https://instrument.example",
        timeout=600,
    )
    assert create.call_args.kwargs == {
        "model": "claude-sonnet-5",
        "messages": [
            {"role": "user", "content": "instrument"},
            {"role": "assistant", "content": "prior answer"},
        ],
        "max_tokens": 4096,
        "system": [
            {
                "type": "text",
                "text": "stable system",
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "output_config": {"effort": "max"},
    }
    assert content == "first second"
    assert usage == {
        "prompt_tokens": 17,
        "completion_tokens": 5,
        "total_tokens": 22,
    }


def test_anthropic_instrumentation_retries_transient_failures(monkeypatch):
    from config import InstrumentationLLMConfig, LLMConfig
    from llm.llm_client import LLMClient

    repair_create = mock.Mock(
        return_value=mock.Mock(
            choices=[mock.Mock(message=mock.Mock(content="repair"))],
            usage=None,
        )
    )
    openai_factory = mock.Mock(
        return_value=mock.Mock(chat=mock.Mock(completions=mock.Mock(create=repair_create)))
    )
    instrumentation_response = mock.Mock(
        content=[{"type": "text", "text": "instrumented"}],
        usage={"input_tokens": 10, "output_tokens": 20},
    )
    create = mock.Mock(
        side_effect=[RuntimeError("temporary"), instrumentation_response]
    )
    anthropic_factory = mock.Mock(
        return_value=mock.Mock(messages=mock.Mock(create=create))
    )
    monkeypatch.setattr("llm.llm_client.OpenAI", openai_factory)
    monkeypatch.setattr(
        "llm.anthropic_instrumentation_client.Anthropic", anthropic_factory
    )
    monkeypatch.setattr(LLMConfig, "MAX_RETRIES", 2)
    monkeypatch.setattr(InstrumentationLLMConfig, "PROVIDER", "anthropic")
    monkeypatch.setattr(InstrumentationLLMConfig, "API_KEY", "instrument-key")
    monkeypatch.setattr(InstrumentationLLMConfig, "BASE_URL", "https://instrument.example")
    monkeypatch.setattr(InstrumentationLLMConfig, "MODEL", "claude-sonnet-5")
    monkeypatch.setattr(InstrumentationLLMConfig, "REASONING_EFFORT", "high")
    monkeypatch.setattr(InstrumentationLLMConfig, "TEMPERATURE", None)

    content, usage = LLMClient().generate_response(
        [{"role": "user", "content": "instrument"}],
        "insert_print",
    )

    assert content == "instrumented"
    assert usage["total_tokens"] == 30
    assert create.call_count == 2


def test_anthropic_repair_still_uses_openai(monkeypatch):
    from config import InstrumentationLLMConfig, LLMConfig
    from llm.llm_client import LLMClient

    repair_create = mock.Mock(return_value=mock.Mock(choices=[mock.Mock(message=mock.Mock(content="repair"))], usage=None))
    openai_factory = mock.Mock(return_value=mock.Mock(chat=mock.Mock(completions=mock.Mock(create=repair_create))))
    anthropic_factory = mock.Mock(return_value=mock.Mock(messages=mock.Mock(create=mock.Mock(return_value=mock.Mock(content=[{"type": "text", "text": "i"}], usage=mock.Mock(input_tokens=10, output_tokens=20))))))

    monkeypatch.setattr("llm.llm_client.OpenAI", openai_factory)
    monkeypatch.setattr("llm.anthropic_instrumentation_client.Anthropic", anthropic_factory)
    monkeypatch.setattr(LLMConfig, "API_KEY", "repair-key")
    monkeypatch.setattr(LLMConfig, "BASE_URL", "https://repair.example/v1")
    monkeypatch.setattr(LLMConfig, "MODEL", "repair-model")
    monkeypatch.setattr(LLMConfig, "REASONING_EFFORT", "")
    monkeypatch.setattr(LLMConfig, "TEMPERATURE", None)
    monkeypatch.setattr(InstrumentationLLMConfig, "PROVIDER", "anthropic")
    monkeypatch.setattr(InstrumentationLLMConfig, "API_KEY", "instrument-key")
    monkeypatch.setattr(InstrumentationLLMConfig, "BASE_URL", "https://instrument.example")
    monkeypatch.setattr(InstrumentationLLMConfig, "MODEL", "claude-sonnet-5")
    monkeypatch.setattr(InstrumentationLLMConfig, "REASONING_EFFORT", "max")
    monkeypatch.setattr(InstrumentationLLMConfig, "TEMPERATURE", None)

    client = LLMClient()
    client.generate_response([{"role": "user", "content": "fix bug"}], "debug_repair")

    assert repair_create.call_args.kwargs["model"] == "repair-model"
    assert "reasoning_effort" not in repair_create.call_args.kwargs
