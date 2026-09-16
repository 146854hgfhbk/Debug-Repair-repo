from pathlib import Path
import subprocess
from types import SimpleNamespace

from utils.java_rule_instrumenter import (
    ensure_instrumenter_built,
    instrument_method_source,
)
from utils.rule_based_insert_print import rule_based_instrument_method


def test_java_helper_build_is_cached():
    first_classpath = ensure_instrumenter_built(force=True)
    main_class = (
        Path(first_classpath[0])
        / "debugrepair"
        / "instrumentation"
        / "InstrumenterMain.class"
    )
    first_mtime = main_class.stat().st_mtime_ns

    second_classpath = ensure_instrumenter_built()

    assert second_classpath == first_classpath
    assert main_class.stat().st_mtime_ns == first_mtime


def test_preserves_signature_comment_and_adds_method_markers():
    source = """
@Deprecated
public <T extends Comparable<T>> T choose(T value) {
    // keep this source comment
    return value;
}
"""

    result = instrument_method_source(source)

    assert "@Deprecated" in result
    assert "<T extends Comparable<T>>" in result
    assert "// keep this source comment" in result
    assert 'System.out.println("// START_DEBUG");' in result
    assert 'System.out.println("// END_DEBUG");' in result


def test_existing_rule_api_delegates_to_lexical_preserving_instrumenter():
    source = """
@Deprecated
public <T extends Comparable<T>> T choose(T value) {
    // this comment must survive the rule pipeline
    return value;
}
"""

    result = rule_based_instrument_method(
        SimpleNamespace(buggy_method=source),
        "// START_DEBUG",
        "// END_DEBUG",
    )

    assert "@Deprecated" in result
    assert "<T extends Comparable<T>>" in result
    assert "// this comment must survive the rule pipeline" in result


def test_instruments_algorithm_rules_inside_nested_statement_lists():
    source = """
int compute(int x) {
    try {
        int left = x + 1, right = x + 2;
        if (left > 2) {
            return right;
        }
    } catch (RuntimeException ex) {
        x = 0;
        throw ex;
    } finally {
        x = x + 1;
    }
    switch (x) {
        case 1:
            x = 2;
            break;
        default:
            x = 3;
    }
    return x;
}
"""

    result = instrument_method_source(source)

    assert "// DEBUG [VAR] left,right = " in result
    assert result.count("// DEBUG [VAR]") == 5
    assert "// DEBUG [COND] left > 2 = " in result
    assert result.count("// DEBUG [RETURN]") == 2
    assert result.count("// END_DEBUG") >= 3
    assert result.index("// END_DEBUG", result.index("catch")) < result.index("throw ex")


def test_loop_and_return_expressions_are_evaluated_once(tmp_path):
    method = instrument_method_source(
        """
static int work() {
    int visits = 0;
    while (shouldContinue()) {
        visits = visits + 1;
    }
    return finish(visits);
}
"""
    )
    source = f"""
public class RuntimeSubject {{
    static int checks = 0;
    static int finishes = 0;

    static boolean shouldContinue() {{
        return checks++ < 2;
    }}

    static int finish(int value) {{
        finishes++;
        return value;
    }}

{method}

    public static void main(String[] args) {{
        int result = work();
        if (result != 2 || checks != 3 || finishes != 1) {{
            throw new AssertionError(
                "result=" + result + ", checks=" + checks + ", finishes=" + finishes);
        }}
    }}
}}
"""
    java_file = tmp_path / "RuntimeSubject.java"
    java_file.write_text(source, encoding="utf-8")

    assert "while (true)" in method
    assert "// DEBUG [LOOP] shouldContinue() = " in method
    assert "if (!__debug_loop_" in method
    assert "// DEBUG [RETURN]" in method
    subprocess.run(["javac", str(java_file)], check=True, capture_output=True, text=True)
    subprocess.run(
        ["java", "-cp", str(tmp_path), "RuntimeSubject"],
        check=True,
        capture_output=True,
        text=True,
    )


def test_primitive_assignment_capture_does_not_require_autoboxing():
    method = instrument_method_source(
        """
static int normalize(int startIndex) {
    startIndex = startIndex < 0 ? 0 : startIndex;
    return startIndex;
}
"""
    )

    assert "String __debug_assignment_" in method
    assert '"" + (startIndex = startIndex < 0 ? 0 : startIndex)' in method
    assert "Object __debug_assignment_" not in method


def test_assignment_target_with_side_effect_is_not_read_twice(tmp_path):
    method = instrument_method_source(
        """
static void update() {
    values[index++] = 7;
}
"""
    )
    source = f"""
public class AssignmentSubject {{
    static int index = 0;
    static int[] values = new int[2];

{method}

    public static void main(String[] args) {{
        update();
        if (index != 1 || values[0] != 7) {{
            throw new AssertionError("index=" + index);
        }}
    }}
}}
"""
    java_file = tmp_path / "AssignmentSubject.java"
    java_file.write_text(source, encoding="utf-8")

    assert "// DEBUG [VAR] values[index++] = " in method
    subprocess.run(["javac", str(java_file)], check=True, capture_output=True, text=True)
    subprocess.run(
        ["java", "-cp", str(tmp_path), "AssignmentSubject"],
        check=True,
        capture_output=True,
        text=True,
    )


def test_exhaustive_switch_does_not_get_unreachable_natural_exit(tmp_path):
    method = instrument_method_source(
        """
static void visit(int value) {
    switch (value) {
        case 0:
            return;
        default:
            return;
    }
}
"""
    )
    source = f"""
public class ExhaustiveSwitchSubject {{
{method}

    public static void main(String[] args) {{
        visit(0);
        visit(1);
    }}
}}
"""
    java_file = tmp_path / "ExhaustiveSwitchSubject.java"
    java_file.write_text(source, encoding="utf-8")

    assert method.count("// END_DEBUG") == 2
    subprocess.run(["javac", str(java_file)], check=True, capture_output=True, text=True)
    subprocess.run(
        ["java", "-cp", str(tmp_path), "ExhaustiveSwitchSubject"],
        check=True,
        capture_output=True,
        text=True,
    )


def test_nested_break_does_not_make_infinite_loop_complete_normally(tmp_path):
    method = instrument_method_source(
        """
static int choose(boolean enterInnerLoop) {
    for (;;) {
        while (enterInnerLoop) {
            break;
        }
        return 7;
    }
}
"""
    )
    source = f"""
public class NestedBreakSubject {{
{method}

    public static void main(String[] args) {{
        if (choose(false) != 7 || choose(true) != 7) {{
            throw new AssertionError();
        }}
    }}
}}
"""
    java_file = tmp_path / "NestedBreakSubject.java"
    java_file.write_text(source, encoding="utf-8")

    assert method.count("// END_DEBUG") == 1
    subprocess.run(["javac", str(java_file)], check=True, capture_output=True, text=True)
    subprocess.run(
        ["java", "-cp", str(tmp_path), "NestedBreakSubject"],
        check=True,
        capture_output=True,
        text=True,
    )


def test_loop_condition_assignment_remains_definitely_assigned(tmp_path):
    method = instrument_method_source(
        """
static int readInto(byte[] destination) {
    int offset = 0;
    int value;
    while (offset < destination.length && ((value = next()) >= 0)) {
        destination[offset++] = (byte) value;
    }
    return offset;
}
"""
    )
    source = f"""
public class DefiniteAssignmentSubject {{
    static int calls = 0;

    static int next() {{
        return calls++ == 0 ? 65 : -1;
    }}

{method}

    public static void main(String[] args) {{
        byte[] destination = new byte[2];
        int count = readInto(destination);
        if (count != 1 || destination[0] != 65 || calls != 2) {{
            throw new AssertionError(
                "count=" + count + ", value=" + destination[0] + ", calls=" + calls);
        }}
    }}
}}
"""
    java_file = tmp_path / "DefiniteAssignmentSubject.java"
    java_file.write_text(source, encoding="utf-8")

    assert "// DEBUG [LOOP]" in method
    subprocess.run(["javac", str(java_file)], check=True, capture_output=True, text=True)
    subprocess.run(
        ["java", "-cp", str(tmp_path), "DefiniteAssignmentSubject"],
        check=True,
        capture_output=True,
        text=True,
    )


def test_constructor_marker_follows_explicit_invocation_and_has_natural_exit():
    result = instrument_method_source(
        """
Box() {
    this(1);
}
"""
    )

    assert result.index("this(1);") < result.index("// START_DEBUG")
    assert result.index("// START_DEBUG") < result.index("// END_DEBUG")


def test_generated_names_do_not_collide_with_user_variables():
    result = instrument_method_source(
        """
int choose(boolean input) {
    boolean __debug_cond_0 = input;
    if (input) {
        return 1;
    }
    return 0;
}
"""
    )

    assert result.count("boolean __debug_cond_0") == 1
    assert "boolean __debug_cond_1" in result


def test_condition_text_with_string_literal_is_escaped():
    result = instrument_method_source(
        """
boolean empty(String value) {
    if (value.equals("")) {
        return true;
    }
    return false;
}
"""
    )

    assert 'value.equals(\\"\\")' in result


def test_does_not_instrument_nested_anonymous_callable():
    result = instrument_method_source(
        """
int outer() {
    Object nested = new Object() {
        int inner() {
            return 1;
        }
    };
    return 2;
}
"""
    )

    assert result.count("// START_DEBUG") == 1
    assert result.count("// DEBUG [RETURN]") == 1
