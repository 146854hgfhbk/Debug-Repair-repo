  public void testNoInlineDeletedProperties() {
    testSameLocal(
        "var foo = {bar:1};" +
        "delete foo.bar;" +
        "return foo.bar;");
  }