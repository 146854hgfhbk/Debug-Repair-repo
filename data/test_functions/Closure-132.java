  public void testIssue925() {
    test(
        "if (x[--y] === 1) {\n" +
        "    x[y] = 0;\n" +
        "} else {\n" +
        "    x[y] = 1;\n" +
        "}",
        "(x[--y] === 1) ? x[y] = 0 : x[y] = 1;");

    test(
        "if (x[--y]) {\n" +
        "    a = 0;\n" +
        "} else {\n" +
        "    a = 1;\n" +
        "}",
        "a = (x[--y]) ? 0 : 1;");

    test("if (x++) { x += 2 } else { x += 3 }",
         "x++ ? x += 2 : x += 3");

    test("if (x++) { x = x + 2 } else { x = x + 3 }",
        "x = x++ ? x + 2 : x + 3");
  }