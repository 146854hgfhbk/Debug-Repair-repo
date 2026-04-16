  public void testIssue1058() throws Exception {
    testTypes(
        "/**\n" +
        "  * @constructor\n" +
        "  * @template CLASS\n" +
        "  */\n" +
        "var Class = function() {};\n" +
        "\n" +
        "/**\n" +
        "  * @param {function(CLASS):CLASS} a\n" +
        "  * @template T\n" +
        "  */\n" +
        "Class.prototype.foo = function(a) {\n" +
        "  return 'string';\n" +
        "};\n" +
        "\n" +
        "/** @param {number} a\n" +
        "  * @return {string} */\n" +
        "var a = function(a) { return '' };\n" +
        "\n" +
        "new Class().foo(a);");
  }