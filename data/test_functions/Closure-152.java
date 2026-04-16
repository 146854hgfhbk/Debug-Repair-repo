  public void testBackwardsTypedefUse1() throws Exception {
    testTypes(
        "/** @this {MyTypedef} */ function f() {}" +
        "/** @typedef {string} */ var MyTypedef;",
        "@this type of a function must be an object\n" +
        "Actual type: string");
  }