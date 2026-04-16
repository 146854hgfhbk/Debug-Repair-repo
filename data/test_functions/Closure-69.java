  public void testThisTypeOfFunction2() throws Exception {
    testTypes(
        "/** @constructor */ function F() {}" +
        "/** @type {function(this:F)} */ function f() {}" +
        "f();",
        "\"function (this:F): ?\" must be called with a \"this\" type");
  }