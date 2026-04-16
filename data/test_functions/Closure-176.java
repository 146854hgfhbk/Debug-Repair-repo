  public void testIssue1056() throws Exception {
    testTypes(
        "/** @type {Array} */ var x = null;" +
        "x.push('hi');",
        "No properties on this expression\n" +
        "found   : null\n" +
        "required: Object");
  }