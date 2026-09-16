from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
import os
import locale
import shutil
import subprocess
import sys
import tempfile
from urllib.request import urlopen


TOOL_ROOT = Path(__file__).resolve().parent
BUILD_ROOT = TOOL_ROOT / "build"
DEPENDENCY_ROOT = BUILD_ROOT / "dependencies"
CLASSES_ROOT = BUILD_ROOT / "classes"
SOURCE_FILE = (
    TOOL_ROOT
    / "src"
    / "main"
    / "java"
    / "debugrepair"
    / "instrumentation"
    / "InstrumenterMain.java"
)
MAIN_CLASS_FILE = (
    CLASSES_ROOT
    / "debugrepair"
    / "instrumentation"
    / "InstrumenterMain.class"
)

JAVAPARSER_VERSION = "3.26.3"
JAVAPARSER_JAR = (
    DEPENDENCY_ROOT / f"javaparser-core-{JAVAPARSER_VERSION}.jar"
)
JAVAPARSER_URL = (
    "https://repo.maven.apache.org/maven2/com/github/javaparser/"
    f"javaparser-core/{JAVAPARSER_VERSION}/"
    f"javaparser-core-{JAVAPARSER_VERSION}.jar"
)
JAVAPARSER_SHA256 = (
    "a24c4fa7799ffe0c7a9af11d4eecd757098ed4498f86067bf28b46b2bfea1833"
)


class BuildError(RuntimeError):
    pass


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_dependency() -> None:
    DEPENDENCY_ROOT.mkdir(parents=True, exist_ok=True)
    if JAVAPARSER_JAR.exists():
        if _file_sha256(JAVAPARSER_JAR) == JAVAPARSER_SHA256:
            return
        JAVAPARSER_JAR.unlink()

    fd, temporary_name = tempfile.mkstemp(
        prefix="javaparser-", suffix=".jar", dir=str(DEPENDENCY_ROOT)
    )
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        with urlopen(JAVAPARSER_URL, timeout=60) as response:
            with temporary_path.open("wb") as output:
                shutil.copyfileobj(response, output)
        actual_hash = _file_sha256(temporary_path)
        if actual_hash != JAVAPARSER_SHA256:
            raise BuildError(
                "JavaParser dependency checksum mismatch: "
                f"expected {JAVAPARSER_SHA256}, got {actual_hash}"
            )
        os.replace(temporary_path, JAVAPARSER_JAR)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _needs_compile(force: bool) -> bool:
    if force or not MAIN_CLASS_FILE.exists():
        return True
    class_mtime = MAIN_CLASS_FILE.stat().st_mtime_ns
    return any(
        path.stat().st_mtime_ns > class_mtime
        for path in (SOURCE_FILE, JAVAPARSER_JAR)
    )


def build(force: bool = False) -> list[Path]:
    if not SOURCE_FILE.exists():
        raise BuildError(f"Java helper source is missing: {SOURCE_FILE}")
    _download_dependency()

    if _needs_compile(force):
        CLASSES_ROOT.mkdir(parents=True, exist_ok=True)
        command = [
            "javac",
            "-encoding",
            "UTF-8",
            "-source",
            "8",
            "-target",
            "8",
            "-cp",
            str(JAVAPARSER_JAR),
            "-d",
            str(CLASSES_ROOT),
            str(SOURCE_FILE),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding=locale.getpreferredencoding(False),
                errors="replace",
                check=False,
            )
        except OSError as exc:
            raise BuildError(f"Unable to execute javac: {exc}") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise BuildError(f"javac failed: {detail}")

    if not MAIN_CLASS_FILE.exists():
        raise BuildError(f"javac did not create {MAIN_CLASS_FILE}")
    return [CLASSES_ROOT.resolve(), JAVAPARSER_JAR.resolve()]


def main() -> int:
    parser = ArgumentParser(description="Build the JavaParser instrumentation helper")
    parser.add_argument("--force", action="store_true", help="force javac recompilation")
    parser.add_argument(
        "--print-classpath",
        action="store_true",
        help="print the runtime classpath to stdout",
    )
    arguments = parser.parse_args()
    try:
        classpath = build(force=arguments.force)
    except (BuildError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if arguments.print_classpath:
        print(os.pathsep.join(str(path) for path in classpath))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
