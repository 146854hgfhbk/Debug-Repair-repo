import argparse
import os

from config import ClientConfig, InstrumentationLLMConfig, LLMConfig


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required deployment setting: {name}")
    return value


def _configure_llm() -> None:
    LLMConfig.LLM_MODEL = _required_env("DEBUGREPAIR_LLM_LABEL")
    LLMConfig.BASE_URL = _required_env("DEBUGREPAIR_LLM_BASE_URL")
    LLMConfig.MODEL = _required_env("DEBUGREPAIR_LLM_MODEL")
    LLMConfig.API_KEY = _required_env("DEBUGREPAIR_LLM_API_KEY")
    LLMConfig.REASONING_EFFORT = ""
    temperature = os.environ.get("DEBUGREPAIR_LLM_TEMPERATURE", "").strip()
    LLMConfig.TEMPERATURE = float(temperature) if temperature else 1.0
    InstrumentationLLMConfig.BASE_URL = (
        os.environ.get("DEBUGREPAIR_INSTRUMENT_LLM_BASE_URL", "").strip()
        or LLMConfig.BASE_URL
    )
    InstrumentationLLMConfig.MODEL = (
        os.environ.get("DEBUGREPAIR_INSTRUMENT_LLM_MODEL", "").strip()
        or LLMConfig.MODEL
    )
    InstrumentationLLMConfig.API_KEY = (
        os.environ.get("DEBUGREPAIR_INSTRUMENT_LLM_API_KEY", "").strip()
        or LLMConfig.API_KEY
    )
    InstrumentationLLMConfig.REASONING_EFFORT = os.environ.get(
        "DEBUGREPAIR_INSTRUMENT_LLM_REASONING_EFFORT", ""
    ).strip()
    InstrumentationLLMConfig.PROVIDER = (
        os.environ.get("DEBUGREPAIR_INSTRUMENT_LLM_PROVIDER", "openai")
        .strip()
        .lower()
    )
    if InstrumentationLLMConfig.PROVIDER not in ("openai", "anthropic"):
        raise SystemExit(
            f"Unsupported instrumentation provider: {InstrumentationLLMConfig.PROVIDER}. "
            f"Supported: openai, anthropic"
        )


def _run_configured_workflow() -> None:
    from runner import run

    if ClientConfig.DEFAULT:
        run()
    elif ClientConfig.RANGE:
        run(list(range(ClientConfig.RANGE_START, ClientConfig.RANGE_END + 1)))
    elif ClientConfig.CUSTOM:
        run(ClientConfig.CUSTOM_LIST)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load server-only LLM settings and start DebugRepair."
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="validate deployment settings without contacting the LLM API",
    )
    args = parser.parse_args()

    _configure_llm()
    if args.check_config:
        print(f"LLM label: {LLMConfig.LLM_MODEL}")
        print(f"Model: {LLMConfig.MODEL}")
        print("Repair reasoning effort: omitted")
        print(f"Instrumentation provider: {InstrumentationLLMConfig.PROVIDER}")
        print(f"Instrumentation model: {InstrumentationLLMConfig.MODEL}")
        print(
            "Instrumentation reasoning effort: "
            f"{InstrumentationLLMConfig.REASONING_EFFORT}"
        )
        print("Instrumentation base URL: configured")
        print("Instrumentation API key: configured")
        print("Base URL: configured")
        print("API key: configured")
        return 0

    _run_configured_workflow()
    print("------Done------")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
