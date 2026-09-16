import os
import shutil
import subprocess
import tempfile

from config import BasicConfig, LLMConfig, ValidatorConfig
from defs.bug_info import BugInfo
from utils.java_rule_instrumenter import replace_method_source
from utils.timeout_utils import timeout


TRIGGER_START_MARKER = "\nNow runtime output for trigger test begin:\n"
SINGLE_TEST_RUNNER_SOURCE = """\
import java.lang.reflect.Method;
import java.util.Enumeration;

public final class SingleTestRunner {
    private SingleTestRunner() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            throw new IllegalArgumentException("Expected test class and method name.");
        }
        Class<?> testClass = Class.forName(args[0]);
        boolean successful;
        try {
            successful = runJUnit4(testClass, args[1]);
        } catch (ClassNotFoundException missingJUnit4) {
            successful = runJUnit3(testClass, args[1]);
        }
        if (!successful) {
            System.exit(1);
        }
    }

    private static boolean runJUnit4(Class<?> testClass, String methodName)
            throws Exception {
        Class<?> coreClass = Class.forName("org.junit.runner.JUnitCore");
        Class<?> requestClass = Class.forName("org.junit.runner.Request");
        Class<?> resultClass = Class.forName("org.junit.runner.Result");
        Object request = requestClass
                .getMethod("method", Class.class, String.class)
                .invoke(null, testClass, methodName);
        Object core = coreClass.getDeclaredConstructor().newInstance();
        Object result = coreClass.getMethod("run", requestClass).invoke(core, request);
        Iterable<?> failures = (Iterable<?>) resultClass
                .getMethod("getFailures")
                .invoke(result);
        for (Object failure : failures) {
            printFailure(failure);
        }
        return (Boolean) resultClass.getMethod("wasSuccessful").invoke(result);
    }

    private static boolean runJUnit3(Class<?> testClass, String methodName)
            throws Exception {
        Class<?> testCaseClass = Class.forName("junit.framework.TestCase");
        Class<?> resultClass = Class.forName("junit.framework.TestResult");
        if (!testCaseClass.isAssignableFrom(testClass)) {
            throw new IllegalArgumentException(
                    "JUnit 3 test does not extend TestCase: " + testClass.getName());
        }
        Object test = testClass.getDeclaredConstructor().newInstance();
        testCaseClass.getMethod("setName", String.class).invoke(test, methodName);
        Object result = resultClass.getDeclaredConstructor().newInstance();
        testCaseClass.getMethod("run", resultClass).invoke(test, result);
        printFailures((Enumeration<?>) resultClass.getMethod("failures").invoke(result));
        printFailures((Enumeration<?>) resultClass.getMethod("errors").invoke(result));
        return (Boolean) resultClass.getMethod("wasSuccessful").invoke(result);
    }

    private static void printFailures(Enumeration<?> failures) throws Exception {
        while (failures.hasMoreElements()) {
            printFailure(failures.nextElement());
        }
    }

    private static void printFailure(Object failure) throws Exception {
        System.err.println(failure.toString());
        try {
            Method trace = failure.getClass().getMethod("getTrace");
            System.err.println(trace.invoke(failure));
        } catch (NoSuchMethodException noJUnit4Trace) {
            Method trace = failure.getClass().getMethod("trace");
            System.err.println(trace.invoke(failure));
        }
    }
}
"""


def check_instrumented_compiles(
    bug_id: str,
    bug_info: BugInfo,
    instrumented_method: str,
) -> tuple[bool, str]:
    """Compile an instrumented method in an isolated Defects4J checkout."""
    # Check for remote delegation
    try:
        from utils import remote_validation
        if remote_validation.is_remote_validation_enabled():
            result = remote_validation.request_remote_validation(
                "check_instrumented_compiles", bug_id, instrumented_method
            )
            return tuple(result)
    except ImportError:
        pass
    except remote_validation.RemoteValidationError:
        raise

    if not instrumented_method or not instrumented_method.strip():
        return False, "instrumented method is empty"

    project, defect_id = bug_id.split("-", 1)
    compile_root = os.path.join(
        BasicConfig.TEMP_PATH,
        BasicConfig.MODE,
        LLMConfig.LLM_MODEL,
        "instrumentation_compile",
    )
    os.makedirs(compile_root, exist_ok=True)
    checkout_path = tempfile.mkdtemp(prefix=f"{bug_id}-", dir=compile_root)

    try:
        checkout = _run_defects4j(
            [
                "checkout",
                "-p",
                project,
                "-v",
                f"{defect_id}b",
                "-w",
                checkout_path,
            ]
        )
        if checkout.returncode != 0:
            return False, _command_diagnostic("checkout", checkout)

        source_dir = _export_directory(checkout_path, "dir.src.classes")
        source_file = os.path.join(
            checkout_path,
            source_dir,
            _buggy_source_relative_path(bug_id),
        )
        _replace_buggy_method(source_file, bug_info, instrumented_method)

        compile_result = _run_defects4j(["compile"], cwd=checkout_path)
        if compile_result.returncode != 0:
            return False, _command_diagnostic("compile", compile_result)
        return True, ""
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        return False, f"instrumentation compile check failed: {exc}"
    finally:
        shutil.rmtree(checkout_path, ignore_errors=True)


@timeout(ValidatorConfig.COLLECT_OUTPUT_TIMEOUT_LIMIT)
def _collect_output_local(
    bug_id: str,
    bug_info: BugInfo,
    instrumented_method: str,
) -> str:
    """Local implementation: Run one purified trigger against an instrumented buggy method."""
    project, defect_id = bug_id.split("-", 1)
    temp_path = os.path.join(
        BasicConfig.TEMP_PATH,
        BasicConfig.MODE,
        LLMConfig.LLM_MODEL,
        "test_" + bug_id,
    )
    _delete_dir(temp_path)

    try:
        checkout = _run_defects4j(
            [
                "checkout",
                "-p",
                project,
                "-v",
                f"{defect_id}b",
                "-w",
                temp_path,
            ]
        )
        _require_success("checkout", checkout)

        trigger_export = _run_defects4j(
            ["export", "-p", "tests.trigger", "-w", temp_path]
        )
        _require_success("trigger export", trigger_export)
        test_class, test_method, purified_test, test_source_class = _select_purified_trigger(
            bug_info,
            _parse_trigger_tests(trigger_export.stdout),
        )

        test_dir = _export_directory(temp_path, "dir.src.tests")
        test_file = os.path.join(
            temp_path,
            test_dir,
            test_source_class.replace(".", os.sep) + ".java",
        )
        if not _replace_test_function(
            test_file,
            test_method,
            purified_test,
        ):
            raise RuntimeError(
                f"Failed to replace purified test {test_class}::{test_method}"
            )

        source_dir = _export_directory(temp_path, "dir.src.classes")
        source_file = os.path.join(
            temp_path,
            source_dir,
            _buggy_source_relative_path(bug_id),
        )
        patched_source = _replace_buggy_method(
            source_file,
            bug_info,
            instrumented_method,
        )
        _write_debug_preview(bug_id, patched_source)

        _, output = _run_and_collect_output(
            test_class,
            test_method,
            temp_path,
        )
        return output
    finally:
        _delete_dir(temp_path)


def collect_output(
    bug_id: str,
    bug_info: BugInfo,
    instrumented_method: str,
) -> str:
    """Run one purified trigger against an instrumented buggy method."""
    # Check for remote delegation
    try:
        from utils import remote_validation
        if remote_validation.is_remote_validation_enabled():
            result = remote_validation.request_remote_validation(
                "collect_output", bug_id, instrumented_method
            )
            return result
    except ImportError:
        pass
    except remote_validation.RemoteValidationError:
        raise

    return _collect_output_local(bug_id, bug_info, instrumented_method)


def _run_defects4j(args, cwd=None):
    return subprocess.run(
        [ValidatorConfig.DEFECTS4J_EXECUTABLE, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=ValidatorConfig.COLLECT_OUTPUT_TIMEOUT_LIMIT,
        check=False,
        env=os.environ.copy(),
    )


def _require_success(stage: str, completed: subprocess.CompletedProcess) -> None:
    if completed.returncode != 0:
        raise RuntimeError(_command_diagnostic(stage, completed))


def _command_diagnostic(stage: str, completed: subprocess.CompletedProcess) -> str:
    detail = (completed.stderr or completed.stdout or "").strip()
    return f"Defects4J {stage} failed ({completed.returncode}): {detail}"


def _export_directory(temp_path: str, property_name: str) -> str:
    completed = _run_defects4j(
        ["export", "-p", property_name, "-w", temp_path]
    )
    _require_success(f"{property_name} export", completed)
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"Defects4J exported an empty {property_name}")
    return lines[-1]


def _buggy_source_relative_path(bug_id: str) -> str:
    location_path = os.path.join(BasicConfig.LOC_PATH, f"{bug_id}.buggy.lines")
    with open(location_path, "r", encoding="utf-8") as stream:
        paths = {
            line.split("#", 1)[0]
            for line in stream.read().splitlines()
            if line.strip()
        }
    if len(paths) != 1:
        raise ValueError(
            f"Expected one buggy source file for {bug_id}, found {len(paths)}"
        )
    return paths.pop()


def _read_java_source(path: str) -> tuple[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as stream:
            return stream.read(), "utf-8"
    except UnicodeDecodeError:
        with open(path, "r", encoding="ISO-8859-1") as stream:
            return stream.read(), "ISO-8859-1"


def _replace_buggy_method(
    source_file: str,
    bug_info: BugInfo,
    replacement_method: str,
) -> str:
    source, encoding = _read_java_source(source_file)
    source_lines = source.splitlines()
    if not 1 <= bug_info.start_line <= bug_info.end_line <= len(source_lines):
        raise ValueError(
            "Buggy method line range is outside the checked-out source: "
            f"{bug_info.start_line}-{bug_info.end_line} of {len(source_lines)}"
        )

    patched_source = "\n".join(
        source_lines[: bug_info.start_line - 1]
        + replacement_method.splitlines()
        + source_lines[bug_info.end_line :]
    )
    with open(source_file, "w", encoding=encoding) as stream:
        stream.write(patched_source)
    return patched_source


def _parse_trigger_tests(exported: str) -> list[str]:
    triggers = []
    for line in exported.splitlines():
        selector = line.strip()
        if selector.startswith("---"):
            selector = selector[3:].strip()
        if "::" in selector:
            triggers.append(selector)
    if not triggers:
        raise ValueError("Defects4J exported no trigger tests")
    return triggers


def _select_purified_trigger(
    bug_info: BugInfo,
    exported_triggers: list[str],
) -> tuple[str, str, str, str]:
    candidates = {}
    for test in getattr(bug_info, "failing_tests", []) or []:
        test_class = _normalize_test_class(test.get("test_file_path") or "")
        test_method = (test.get("test_method_name") or "").strip()
        if test_class and test_method:
            test_source_class = _normalize_test_class(
                test.get("test_source_file_path") or test_class
            ).strip()
            candidates[(test_class, test_method)] = (
                (test.get("sliced_test") or "").strip(),
                test_source_class,
            )

    matched_empty = []
    for selector in exported_triggers:
        test_class, test_method = selector.split("::", 1)
        key = (_normalize_test_class(test_class), test_method.strip())
        if key not in candidates:
            continue
        purified_test, test_source_class = candidates[key]
        if purified_test:
            return key[0], key[1], purified_test, test_source_class
        matched_empty.append(f"{key[0]}::{key[1]}")

    if matched_empty:
        raise ValueError(
            "Purified test unavailable for exported trigger(s): "
            + ", ".join(matched_empty)
        )
    raise ValueError(
        f"No purified metadata for an exported trigger of {bug_info.bug_id}"
    )


def _load_test_function_code(
    bug_info: BugInfo,
    test_class: str,
    test_function_name: str,
) -> str:
    """Return the purified method matching the selected Defects4J trigger."""
    normalized_class = _normalize_test_class(test_class)
    for test in getattr(bug_info, "failing_tests", []) or []:
        candidate_class = _normalize_test_class(test.get("test_file_path") or "")
        candidate_method = (test.get("test_method_name") or "").strip()
        if candidate_class != normalized_class or candidate_method != test_function_name:
            continue
        sliced_test = (test.get("sliced_test") or "").strip()
        if sliced_test:
            return sliced_test

    raise ValueError(
        "Purified test unavailable for "
        f"{bug_info.bug_id}: {test_class}::{test_function_name}"
    )


def _normalize_test_class(value: str) -> str:
    normalized = value.strip().replace("/", ".").replace("\\", ".")
    if normalized.endswith(".java"):
        normalized = normalized[:-5]
    return normalized


def _replace_test_function(
    test_file_path: str,
    test_function_name: str,
    new_test_code: str,
) -> bool:
    try:
        source, encoding = _read_java_source(test_file_path)
        replaced = replace_method_source(
            source,
            test_function_name,
            new_test_code,
            TRIGGER_START_MARKER,
        )
        with open(test_file_path, "w", encoding=encoding) as stream:
            stream.write(replaced)
        return True
    except Exception as exc:
        print(f"[ERROR] Failed to replace purified test method: {exc}")
        return False


def _run_and_collect_output(test_class, test_function_name, temp_path):
    compile_result = _run_defects4j(["compile"], cwd=temp_path)
    if compile_result.returncode != 0:
        return False, _command_diagnostic("compile", compile_result)

    classpath_export = _run_defects4j(
        ["export", "-p", "cp.test"],
        cwd=temp_path,
    )
    if classpath_export.returncode != 0:
        return False, _command_diagnostic("test classpath export", classpath_export)
    classpath_lines = [
        line.strip()
        for line in classpath_export.stdout.splitlines()
        if line.strip()
    ]
    if not classpath_lines:
        return False, "Defects4J exported an empty test classpath"

    runner_dir = tempfile.mkdtemp(prefix=".debugrepair-runner-", dir=temp_path)
    try:
        runner_source = os.path.join(runner_dir, "SingleTestRunner.java")
        with open(runner_source, "w", encoding="utf-8") as stream:
            stream.write(SINGLE_TEST_RUNNER_SOURCE)

        test_classpath = classpath_lines[-1]
        runner_compile = subprocess.run(
            ["javac", "-cp", test_classpath, runner_source],
            cwd=temp_path,
            capture_output=True,
            text=True,
            timeout=ValidatorConfig.COLLECT_OUTPUT_TIMEOUT_LIMIT,
            check=False,
            env=os.environ.copy(),
        )
        if runner_compile.returncode != 0:
            return False, _command_diagnostic("single-test runner compile", runner_compile)

        runtime_classpath = os.pathsep.join([test_classpath, runner_dir])
        test_result = subprocess.run(
            [
                "java",
                "-cp",
                runtime_classpath,
                "SingleTestRunner",
                test_class,
                test_function_name,
            ],
            cwd=temp_path,
            capture_output=True,
            text=True,
            timeout=ValidatorConfig.TRIGGER_TEST_TIMEOUT_LIMIT,
            check=False,
            env=os.environ.copy(),
        )
        combined_output = "\n".join(
            part for part in (test_result.stdout, test_result.stderr) if part
        )
        return test_result.returncode == 0, _extract_debug_info(combined_output)
    finally:
        shutil.rmtree(runner_dir, ignore_errors=True)


def _write_debug_preview(bug_id: str, source: str) -> None:
    if not BasicConfig.DEBUG_MODE:
        return
    os.makedirs(BasicConfig.DEBUG_PATH, exist_ok=True)
    debug_path = os.path.join(BasicConfig.DEBUG_PATH, f"debug_patched_{bug_id}.java")
    with open(debug_path, "w", encoding="utf-8") as stream:
        stream.write(source)


def _delete_dir(path: str) -> None:
    if path and os.path.isdir(path):
        shutil.rmtree(path)


def _extract_debug_info(output: str) -> str:
    lines = output.splitlines()
    trigger_start = next(
        (
            index
            for index, line in enumerate(lines)
            if "Now runtime output for trigger test begin:" in line
        ),
        None,
    )
    if trigger_start is None:
        return ""

    test_case_start = next(
        (
            index
            for index in range(trigger_start, len(lines))
            if lines[index].strip().startswith("========Test Case")
        ),
        trigger_start,
    )
    error_start = next(
        (
            index
            for index in range(test_case_start, len(lines))
            if lines[index].strip().startswith("at ")
        ),
        len(lines),
    )
    return "\n".join(lines[test_case_start:error_start])
