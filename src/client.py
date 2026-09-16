import argparse
import json
import os
from pathlib import Path
import shutil

from config import (
    BasicConfig,
    ClientConfig,
    InstrumentationLLMConfig,
    LLMConfig,
    ValidatorConfig,
)
from runner import run


def _command_available(command: str) -> bool:
    path = Path(command).expanduser()
    if path.parent != Path("."):
        return path.is_file()
    return shutil.which(command) is not None


def check_runtime_environment() -> None:
    """Validate a local run without contacting an LLM API."""
    errors = []
    required_settings = {
        "DEBUGREPAIR_LLM_LABEL": LLMConfig.LLM_MODEL,
        "DEBUGREPAIR_LLM_BASE_URL": LLMConfig.BASE_URL,
        "DEBUGREPAIR_LLM_MODEL": LLMConfig.MODEL,
        "DEBUGREPAIR_LLM_API_KEY": LLMConfig.API_KEY,
        "instrumentation model": InstrumentationLLMConfig.MODEL,
        "instrumentation base URL": InstrumentationLLMConfig.BASE_URL,
        "instrumentation API key": InstrumentationLLMConfig.API_KEY,
    }
    errors.extend(
        f"missing setting: {name}"
        for name, value in required_settings.items()
        if not value
    )

    if InstrumentationLLMConfig.PROVIDER not in {"openai", "anthropic"}:
        errors.append(
            "DEBUGREPAIR_INSTRUMENT_LLM_PROVIDER must be openai or anthropic"
        )

    required_files = [
        Path(BasicConfig.INDEX_MAP_JSON),
        Path(BasicConfig.BUG_INFO_JSON),
        Path(BasicConfig.FAILING_TEST_JSON),
        Path(__file__).resolve().parents[1]
        / "tools"
        / "java-instrumenter"
        / "build.py",
    ]
    errors.extend(
        f"required file not found: {path}"
        for path in required_files
        if not path.is_file()
    )

    for command in ("java", "javac"):
        if not _command_available(command):
            errors.append(f"required command not found on PATH: {command}")

    if not os.getenv("DEBUGREPAIR_VALIDATOR_URL"):
        if not _command_available(ValidatorConfig.DEFECTS4J_EXECUTABLE):
            errors.append(
                "Defects4J executable not found; set DEBUGREPAIR_DEFECTS4J "
                "or add defects4j to PATH"
            )

    if Path(BasicConfig.INDEX_MAP_JSON).is_file():
        with open(BasicConfig.INDEX_MAP_JSON, "r", encoding="utf-8") as stream:
            bug_count = len(json.load(stream))
        if bug_count != 483:
            errors.append(f"expected 483 bug indices, found {bug_count}")

    if errors:
        raise SystemExit(
            "DebugRepair configuration check failed:\n- " + "\n- ".join(errors)
        )

    from utils.java_rule_instrumenter import ensure_instrumenter_built

    ensure_instrumenter_built()
    print("Configuration check passed (no LLM API request was sent).")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run DebugRepair on Defects4J bugs."
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="validate local dependencies and settings without calling an LLM",
    )
    parser.add_argument(
        "--bugs",
        nargs="+",
        type=int,
        metavar="INDEX",
        help="run only the listed 1-based indices from data/bug_info/index_map.json",
    )
    args = parser.parse_args(argv)

    check_runtime_environment()
    if args.check_config:
        return 0

    if args.bugs:
        run(args.bugs)
    elif ClientConfig.DEFAULT:
        run()
    elif ClientConfig.RANGE:
        run(list(range(ClientConfig.RANGE_START, ClientConfig.RANGE_END + 1)))
    elif ClientConfig.CUSTOM:
        run(ClientConfig.CUSTOM_LIST)

    print("------Done------")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
