from pathlib import Path
import base64
import os
import subprocess
import sys
from typing import List


ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = ROOT / "tools" / "java-instrumenter" / "build.py"
MAIN_CLASS = "debugrepair.instrumentation.InstrumenterMain"


class JavaInstrumentationError(RuntimeError):
    """Raised when the JavaParser helper cannot build or instrument source."""


def ensure_instrumenter_built(force: bool = False) -> List[str]:
    command = [sys.executable, str(BUILD_SCRIPT), "--print-classpath"]
    if force:
        command.append("--force")
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise JavaInstrumentationError(
            f"Unable to build the JavaParser instrumenter: {exc}"
        ) from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise JavaInstrumentationError(
            f"Unable to build the JavaParser instrumenter: {detail}"
        )

    classpath = [part for part in completed.stdout.strip().split(os.pathsep) if part]
    if not classpath:
        raise JavaInstrumentationError(
            "The JavaParser instrumenter build returned an empty classpath."
        )
    return classpath


def instrument_method_source(
    source: str,
    start_marker: str = "// START_DEBUG",
    end_marker: str = "// END_DEBUG",
) -> str:
    """Instrument one Java method or constructor through JavaParser."""
    if not source or not source.strip():
        raise ValueError("source must contain a Java method or constructor")

    classpath = os.pathsep.join(ensure_instrumenter_built())
    try:
        completed = subprocess.run(
            ["java", "-cp", classpath, MAIN_CLASS, start_marker, end_marker],
            cwd=str(ROOT),
            input=source,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise JavaInstrumentationError(
            f"Unable to execute the JavaParser instrumenter: {exc}"
        ) from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise JavaInstrumentationError(f"Java instrumentation failed: {detail}")

    result = completed.stdout.strip()
    if not result:
        raise JavaInstrumentationError("Java instrumentation returned no source code.")
    return result


def normalize_method_source(source: str) -> str:
    """Remove Java comments and println statements, then print canonical source."""
    if not source or not source.strip():
        raise ValueError("source must contain a Java method or constructor")

    classpath = os.pathsep.join(ensure_instrumenter_built())
    try:
        completed = subprocess.run(
            ["java", "-cp", classpath, MAIN_CLASS, "--normalize"],
            cwd=str(ROOT),
            input=source,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise JavaInstrumentationError(
            f"Unable to normalize Java source with JavaParser: {exc}"
        ) from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise JavaInstrumentationError(f"Java normalization failed: {detail}")

    result = completed.stdout.strip()
    if not result:
        raise JavaInstrumentationError("Java normalization returned no source code.")
    return result


def replace_method_source(
    compilation_unit_source: str,
    method_name: str,
    replacement_source: str,
    prepended_message: str,
) -> str:
    """Replace one uniquely named method while preserving surrounding Java source."""
    if not compilation_unit_source or not compilation_unit_source.strip():
        raise ValueError("compilation_unit_source must contain a Java type")
    if not method_name or not method_name.strip():
        raise ValueError("method_name must not be empty")
    if not replacement_source or not replacement_source.strip():
        raise ValueError("replacement_source must contain a Java method")

    payload = "\n".join(
        base64.b64encode(value.encode("utf-8")).decode("ascii")
        for value in (compilation_unit_source, replacement_source)
    )
    classpath = os.pathsep.join(ensure_instrumenter_built())
    try:
        completed = subprocess.run(
            [
                "java",
                "-cp",
                classpath,
                MAIN_CLASS,
                "--replace-method",
                method_name,
                prepended_message,
            ],
            cwd=str(ROOT),
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise JavaInstrumentationError(
            f"Unable to replace Java method with JavaParser: {exc}"
        ) from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise JavaInstrumentationError(f"Java method replacement failed: {detail}")

    result = completed.stdout
    if not result.strip():
        raise JavaInstrumentationError("Java method replacement returned no source code.")
    return result
