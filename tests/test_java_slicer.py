"""java_slicer 的行为测试, 基准取自 DebugRepair 论文 3.2 节与 Algorithm 1。"""

import os
import tempfile
import unittest

from utils.java_slicer import analyze_test_with_dependencies


def slice_of(source: str, method: str, assertion: str, line: int = None,
             validator=None) -> dict:
    directory = tempfile.mkdtemp(prefix="slicer_test_")
    path = os.path.join(directory, "T.java")
    with open(path, "w", encoding="utf-8") as f:
        f.write(source)
    return analyze_test_with_dependencies(
        method, "", assertion, path, line, validator=validator)[0]


def body_lines(sliced: str) -> list:
    lines = [l.strip() for l in sliced.strip().split("\n")]
    return [l for l in lines[1:-1] if l]


class TestBackwardSlicing(unittest.TestCase):
    def test_figure3_alias_requires_second_traversal(self):
        """论文 Figure 3: listB 是 listA 的别名, 最终切片必须含 L3。"""
        source = """public class T {
    public void testAlias() {
        List<String> listA = new ArrayList<>();
        List<String> listB = listA;
        listB.add("Bug Trigger!");
        assertEquals(1, listA.size());
    }
}
"""
        result = slice_of(source, "testAlias", "assertEquals(1, listA.size());")
        self.assertEqual(body_lines(result["sliced_method"]), [
            "List<String> listA = new ArrayList<>();",
            "List<String> listB = listA;",
            'listB.add("Bug Trigger!");',
            "assertEquals(1, listA.size());",
        ])

    def test_figure2_timeseries_example(self):
        """论文 Figure 2: 只保留 s2 相关语句, 丢弃 s3 与其他断言。"""
        source = """public class T {
    private static final double EPSILON = 0.0000000001;
    public void testCreateCopy3() throws CloneNotSupportedException {
        TimeSeries s1 = new TimeSeries("S1");
        s1.add(new Year(2009), 100.0);
        s1.add(new Year(2010), 101.0);
        s1.add(new Year(2011), 102.0);
        assertEquals(100.0, s1.getMinY(), EPSILON);
        assertEquals(102.0, s1.getMaxY(), EPSILON);
        TimeSeries s2 = s1.createCopy(0, 1);
        assertEquals(100.0, s2.getMinY(), EPSILON);
        assertEquals(101.0, s2.getMaxY(), EPSILON);
        TimeSeries s3 = s1.createCopy(1, 2);
        assertEquals(101.0, s3.getMinY(), EPSILON);
        assertEquals(102.0, s3.getMaxY(), EPSILON);
    }
}
"""
        result = slice_of(source, "testCreateCopy3",
                          "assertEquals(101.0, s2.getMaxY(), EPSILON);")
        self.assertEqual(body_lines(result["sliced_method"]), [
            'TimeSeries s1 = new TimeSeries("S1");',
            "s1.add(new Year(2009), 100.0);",
            "s1.add(new Year(2010), 101.0);",
            "s1.add(new Year(2011), 102.0);",
            "TimeSeries s2 = s1.createCopy(0, 1);",
            "assertEquals(101.0, s2.getMaxY(), EPSILON);",
        ])
        # EPSILON 是类字段, 应被 D_v 捕获
        self.assertEqual(len(result["dependencies"]["variables"]), 1)
        self.assertIn("EPSILON", result["dependencies"]["variables"][0])

    def test_signature_and_annotations_preserved(self):
        source = """public class T {
    @Test
    public void testSig() throws Exception {
        int x = 1;
        assertEquals(1, x);
    }
}
"""
        result = slice_of(source, "testSig", "assertEquals(1, x);")
        self.assertIn("@Test", result["sliced_method"])
        self.assertIn("throws Exception", result["sliced_method"])

    def test_unrelated_statements_dropped(self):
        source = """public class T {
    public void testDrop() {
        int noise = 42;
        StringBuilder sb = new StringBuilder();
        sb.append("noise");
        int x = 1;
        assertEquals(1, x);
    }
}
"""
        result = slice_of(source, "testDrop", "assertEquals(1, x);")
        self.assertEqual(body_lines(result["sliced_method"]),
                         ["int x = 1;", "assertEquals(1, x);"])

    def test_method_names_do_not_pollute_required_vars(self):
        """add 是方法名而非变量, 不应让无关的 other.add(...) 进入切片。"""
        source = """public class T {
    public void testNames() {
        List<String> target = new ArrayList<>();
        List<String> other = new ArrayList<>();
        other.add("x");
        assertEquals(0, target.size());
    }
}
"""
        result = slice_of(source, "testNames", "assertEquals(0, target.size());")
        self.assertEqual(body_lines(result["sliced_method"]), [
            "List<String> target = new ArrayList<>();",
            "assertEquals(0, target.size());",
        ])

    def test_primitive_does_not_trigger_state_modification_rule(self):
        """基本类型不在 V_use 内: 读取 count 的语句不因隐式修改规则被纳入。"""
        source = """public class T {
    public void testPrimitive() {
        int count = 3;
        int mirror = count;
        int result = count * 2;
        assertEquals(6, result);
    }
}
"""
        result = slice_of(source, "testPrimitive", "assertEquals(6, result);")
        self.assertEqual(body_lines(result["sliced_method"]), [
            "int count = 3;",
            "int result = count * 2;",
            "assertEquals(6, result);",
        ])

    def test_compound_assignment_is_a_definition(self):
        source = """public class T {
    public void testCompound() {
        int total = 1;
        total += 5;
        assertEquals(6, total);
    }
}
"""
        result = slice_of(source, "testCompound", "assertEquals(6, total);")
        self.assertEqual(body_lines(result["sliced_method"]), [
            "int total = 1;", "total += 5;", "assertEquals(6, total);"])

    def test_preceding_asserts_excluded_but_side_effects_kept(self):
        """断言不受隐式修改规则约束, 但有副作用的非断言语句必须留下。"""
        source = """public class T {
    public void testAsserts() {
        List<String> data = new ArrayList<>();
        assertTrue(data.isEmpty());
        data.add("v");
        assertEquals(1, data.size());
    }
}
"""
        result = slice_of(source, "testAsserts", "assertEquals(1, data.size());")
        self.assertEqual(body_lines(result["sliced_method"]), [
            "List<String> data = new ArrayList<>();",
            'data.add("v");',
            "assertEquals(1, data.size());",
        ])

    def test_compound_statement_kept_whole(self):
        source = """public class T {
    public void testLoop() {
        List<String> data = new ArrayList<>();
        for (int i = 0; i < 3; i++) {
            data.add("v" + i);
        }
        assertEquals(3, data.size());
    }
}
"""
        sliced = slice_of(source, "testLoop", "assertEquals(3, data.size());")["sliced_method"]
        self.assertIn("for (int i = 0; i < 3; i++) {", sliced)
        self.assertIn('data.add("v" + i);', sliced)
        self.assertIn("}", sliced)

    def test_static_access_not_treated_as_field(self):
        source = """public class T {
    public void testStatic() {
        int x = 1;
        System.out.println("noise");
        assertEquals(1, x);
    }
}
"""
        result = slice_of(source, "testStatic", "assertEquals(1, x);")
        self.assertEqual(body_lines(result["sliced_method"]),
                         ["int x = 1;", "assertEquals(1, x);"])


class TestDependencyClosure(unittest.TestCase):
    def test_transitive_method_and_field_closure(self):
        source = """public class T {
    private int seed = 7;
    private String unusedField = "no";
    private int helperA() { return helperB() + seed; }
    private int helperB() { return 2; }
    private void unusedHelper() { }
    public void testClosure() {
        int v = helperA();
        assertEquals(9, v);
    }
}
"""
        deps = slice_of(source, "testClosure", "assertEquals(9, v);")["dependencies"]
        methods = " ".join(deps["methods"])
        self.assertIn("helperA", methods)
        self.assertIn("helperB", methods)
        self.assertNotIn("unusedHelper", methods)
        variables = " ".join(deps["variables"])
        self.assertIn("seed", variables)
        self.assertNotIn("unusedField", variables)

    def test_recursive_helper_terminates(self):
        source = """public class T {
    private int fact(int n) { return n <= 1 ? 1 : n * fact(n - 1); }
    public void testRecursive() {
        int v = fact(3);
        assertEquals(6, v);
    }
}
"""
        deps = slice_of(source, "testRecursive", "assertEquals(6, v);")["dependencies"]
        self.assertEqual(len(deps["methods"]), 1)
        self.assertIn("fact", deps["methods"][0])

    def test_mutually_recursive_helpers_terminate(self):
        source = """public class T {
    private boolean isEven(int n) { return n == 0 ? true : isOdd(n - 1); }
    private boolean isOdd(int n) { return n == 0 ? false : isEven(n - 1); }
    public void testMutual() {
        boolean v = isEven(4);
        assertTrue(v);
    }
}
"""
        deps = slice_of(source, "testMutual", "assertTrue(v);")["dependencies"]
        self.assertEqual(len(deps["methods"]), 2)

    def test_external_call_not_reported_as_dependency(self):
        """s1.add(...) 作用于其他对象, 不是 C 定义的方法。"""
        source = """public class T {
    private void add(String v) { }
    public void testExternal() {
        List<String> s1 = new ArrayList<>();
        s1.add("x");
        assertEquals(1, s1.size());
    }
}
"""
        deps = slice_of(source, "testExternal", "assertEquals(1, s1.size());")["dependencies"]
        self.assertEqual(deps["methods"], [])

    def test_overload_resolved_by_arity(self):
        source = """public class T {
    private int make(int a) { return a; }
    private int make(int a, int b) { return a + b; }
    public void testOverload() {
        int v = make(1, 2);
        assertEquals(3, v);
    }
}
"""
        deps = slice_of(source, "testOverload", "assertEquals(3, v);")["dependencies"]
        self.assertEqual(len(deps["methods"]), 1)
        self.assertIn("int a, int b", deps["methods"][0])

    def test_field_used_only_inside_helper_is_captured(self):
        source = """public class T {
    private int hidden = 5;
    private int helper() { return hidden; }
    public void testHidden() {
        int v = helper();
        assertEquals(5, v);
    }
}
"""
        deps = slice_of(source, "testHidden", "assertEquals(5, v);")["dependencies"]
        self.assertIn("hidden", " ".join(deps["variables"]))

    def test_varargs_helper_is_captured(self):
        source = """public class T {
    private int total(int first, int... rest) { return first + rest.length; }
    public void testVarargs() {
        int v = total(1, 2, 3);
        assertEquals(3, v);
    }
}
"""
        deps = slice_of(source, "testVarargs", "assertEquals(3, v);")["dependencies"]
        self.assertEqual(len(deps["methods"]), 1)
        self.assertIn("int... rest", deps["methods"][0])

    def test_dependencies_follow_source_order(self):
        source = """public class T {
    private int first() { return 1; }
    private int second() { return 2; }
    public void testOrder() {
        int v = second() + first();
        assertEquals(3, v);
    }
}
"""
        deps = slice_of(source, "testOrder", "assertEquals(3, v);")["dependencies"]
        self.assertIn("first", deps["methods"][0])
        self.assertIn("second", deps["methods"][1])


class TestFallbacks(unittest.TestCase):
    SOURCE = """public class T {
    public void testDuplicate() {
        int x = 1;
        assertEquals(1, x);
        int y = 2;
        assertEquals(1, x);
    }
    public void testEmpty() {
    }
}
"""

    def test_duplicate_assert_returns_original(self):
        result = slice_of(self.SOURCE, "testDuplicate", "assertEquals(1, x);")
        self.assertIn("重复出现", result["dependencies"]["info"])
        self.assertIn("int y = 2;", result["sliced_method"])

    def test_duplicate_assert_disambiguated_by_line(self):
        result = slice_of(self.SOURCE, "testDuplicate", "assertEquals(1, x);", line=4)
        self.assertEqual(body_lines(result["sliced_method"]),
                         ["int x = 1;", "assertEquals(1, x);"])

    def test_missing_assert_returns_original(self):
        result = slice_of(self.SOURCE, "testDuplicate", "assertEquals(99, z);")
        self.assertIn("未找到目标断言", result["dependencies"]["info"])

    def test_empty_body_returns_original(self):
        result = slice_of(self.SOURCE, "testEmpty", "assertEquals(1, x);")
        self.assertIn("方法体为空", result["dependencies"]["info"])

    def test_missing_file(self):
        result = analyze_test_with_dependencies("t", "", "a", "no_such_file.java")[0]
        self.assertIn("文件未找到", result["sliced_method"])

    def test_method_located_via_source_code(self):
        source = """public class T {
    public void realName() {
        int x = 1;
        assertEquals(1, x);
    }
}
"""
        directory = tempfile.mkdtemp(prefix="slicer_test_")
        path = os.path.join(directory, "T.java")
        with open(path, "w", encoding="utf-8") as f:
            f.write(source)
        result = analyze_test_with_dependencies(
            "wrongName", "public void realName() { int x = 1; assertEquals(1, x); }",
            "assertEquals(1, x);", path)[0]
        self.assertEqual(body_lines(result["sliced_method"]),
                         ["int x = 1;", "assertEquals(1, x);"])

    def test_nested_failing_assert_anchors_on_top_level_statement(self):
        source = """public class T {
    public void testNested() {
        List<String> data = new ArrayList<>();
        data.add("v");
        for (String s : data) {
            assertEquals("v", s);
        }
    }
}
"""
        result = slice_of(source, "testNested", 'assertEquals("v", s);')
        sliced = result["sliced_method"]
        self.assertIn("List<String> data = new ArrayList<>();", sliced)
        self.assertIn('data.add("v");', sliced)
        self.assertIn("for (String s : data) {", sliced)

    def test_syntax_error_returns_original_method(self):
        source = """public class T {
    public void testBroken() {
        int noise = 0;
        int x = ;
        assertEquals(1, x);
    }
}
"""
        result = slice_of(source, "testBroken", "assertEquals(1, x);")
        self.assertEqual(result["status"], "fallback")
        self.assertIn("语法错误", result["diagnostic"])
        self.assertIn("int noise = 0;", result["sliced_method"])


class TestRuntimeValidation(unittest.TestCase):
    SOURCE = """public class T {
    public void testValidation() {
        int noise = 0;
        int x = 1;
        assertEquals(1, x);
    }
}
"""

    def test_validated_slice_is_accepted(self):
        seen = []

        def validator(candidate, dependencies):
            seen.append((candidate, dependencies))
            return {"accepted": True, "diagnostic": "failure preserved"}

        result = slice_of(
            self.SOURCE, "testValidation", "assertEquals(1, x);",
            validator=validator)

        self.assertEqual(result["status"], "validated")
        self.assertNotIn("int noise = 0;", result["sliced_method"])
        self.assertEqual(result["diagnostic"], "failure preserved")
        self.assertEqual(len(seen), 1)

    def test_rejected_slice_falls_back_to_original(self):
        def validator(candidate, dependencies):
            return {
                "accepted": False,
                "diagnostic": "original failure was not reproduced",
            }

        result = slice_of(
            self.SOURCE, "testValidation", "assertEquals(1, x);",
            validator=validator)

        self.assertEqual(result["status"], "fallback")
        self.assertIn("int noise = 0;", result["sliced_method"])
        self.assertEqual(result["diagnostic"],
                         "original failure was not reproduced")

    def test_validator_exception_falls_back_to_original(self):
        def validator(candidate, dependencies):
            raise RuntimeError("validator unavailable")

        result = slice_of(
            self.SOURCE, "testValidation", "assertEquals(1, x);",
            validator=validator)

        self.assertEqual(result["status"], "fallback")
        self.assertIn("validator unavailable", result["diagnostic"])
        self.assertIn("int noise = 0;", result["sliced_method"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
