import json
import os
from pathlib import Path
import subprocess
import sys
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def test_one_model_environment_defaults_instrumentation_to_repair():
    settings = {
        "DEBUGREPAIR_LLM_LABEL": "smoke-model",
        "DEBUGREPAIR_LLM_BASE_URL": "https://model.example/v1",
        "DEBUGREPAIR_LLM_MODEL": "model-id",
        "DEBUGREPAIR_LLM_API_KEY": "test-key",
    }
    environment = os.environ.copy()
    environment.update(settings)
    for name in (
        "DEBUGREPAIR_INSTRUMENT_LLM_BASE_URL",
        "DEBUGREPAIR_INSTRUMENT_LLM_MODEL",
        "DEBUGREPAIR_INSTRUMENT_LLM_API_KEY",
    ):
        environment.pop(name, None)

    program = """
import json
from config import InstrumentationLLMConfig, LLMConfig
from llm.llm_client import LLMClient

LLMClient()
print(json.dumps({
    "label": LLMConfig.LLM_MODEL,
    "repair": [LLMConfig.BASE_URL, LLMConfig.MODEL, LLMConfig.API_KEY],
    "instrument": [
        InstrumentationLLMConfig.BASE_URL,
        InstrumentationLLMConfig.MODEL,
        InstrumentationLLMConfig.API_KEY,
    ],
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=ROOT,
        env={**environment, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    configuration = json.loads(completed.stdout.splitlines()[-1])
    assert configuration == {
        "label": "smoke-model",
        "repair": ["https://model.example/v1", "model-id", "test-key"],
        "instrument": ["https://model.example/v1", "model-id", "test-key"],
    }


def test_javaparser_instrumenter_sources_are_packaged():
    tool_root = ROOT / "tools" / "java-instrumenter"

    assert (tool_root / "build.py").is_file()
    assert (
        tool_root
        / "src"
        / "main"
        / "java"
        / "debugrepair"
        / "instrumentation"
        / "InstrumenterMain.java"
    ).is_file()


def test_runtime_metadata_covers_known_inherited_and_fallback_tests():
    metadata = json.loads(
        (ROOT / "data" / "bug_info" / "failing_test.json").read_text(
            encoding="utf-8"
        )
    )

    cli_test = metadata["Cli-27"]["failing_tests"][0]
    assert cli_test["test_source_file_path"] == "org.apache.commons.cli.ParserTestCase"
    assert "assertEquals(\"selected option\", \"bar\"" in cli_test["sliced_test"]

    jackson_test = metadata["JacksonCore-3"]["failing_tests"][0]
    assert jackson_test["purification_status"] == "fallback"
    assert "p.nextToken()" in jackson_test["sliced_test"]


def test_client_supports_config_check_without_starting_repair(monkeypatch):
    import client

    checked = []
    run = mock.Mock()
    monkeypatch.setattr(client, "check_runtime_environment", lambda: checked.append(True))
    monkeypatch.setattr(client, "run", run)

    assert client.main(["--check-config"]) == 0
    assert checked == [True]
    run.assert_not_called()


def test_client_can_run_one_index_without_editing_source(monkeypatch):
    import client

    run = mock.Mock()
    monkeypatch.setattr(client, "check_runtime_environment", lambda: None)
    monkeypatch.setattr(client, "run", run)

    assert client.main(["--bugs", "1"]) == 0
    run.assert_called_once_with([1])
