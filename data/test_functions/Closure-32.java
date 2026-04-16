  public void testIssue701() {
    // Check ASCII art in license comments.
    String ascii = "/**\n" +
        " * @preserve\n" +
        "   This\n" +
        "     is\n" +
        "       ASCII    ART\n" +
        "*/";
    String result = "/*\n\n" +
        "   This\n" +
        "     is\n" +
        "       ASCII    ART\n" +
        "*/\n";
    testSame(createCompilerOptions(), ascii);
    assertEquals(result, lastCompiler.toSource());
  }