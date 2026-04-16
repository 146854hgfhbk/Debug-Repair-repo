  public void testIssue1047() throws Exception {
    testTypes(
        "/**\n" +
        " * @constructor\n" +
        " */\n" +
        "function C2() {}\n" +
        "\n" +
        "/**\n" +
        " * @constructor\n" +
        " */\n" +
        "function C3(c2) {\n" +
        "  /**\n" +
        "   * @type {C2} \n" +
        "   * @private\n" +
        "   */\n" +
        "  this.c2_;\n" +
        "\n" +
        "  var x = this.c2_.prop;\n" +
        "}",
        "Property prop never defined on C2");
  }