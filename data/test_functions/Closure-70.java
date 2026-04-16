  public void testDuplicateLocalVarDecl() throws Exception {
    testClosureTypesMultipleWarnings(
        "/** @param {number} x */\n" +
        "function f(x) { /** @type {string} */ var x = ''; }",
        Lists.newArrayList(
            "variable x redefined with type string, original definition" +
            " at  [testcode] :2 with type number",
            "initializing variable\n" +
            "found   : string\n" +
            "required: number"));
  }