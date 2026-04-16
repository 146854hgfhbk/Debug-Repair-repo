  public void testMethodInference7() throws Exception {
    testTypes(
        "/** @constructor */ function F() {}" +
        "F.prototype.foo = function() { };" +
        "/** @constructor \n * @extends {F} */ " +
        "function G() {}" +
        "/** @override */ G.prototype.foo = function(x, y) { };",
        "mismatch of the foo property type and the type of the property " +
        "it overrides from superclass F\n" +
        "original: function (this:F): undefined\n" +
        "override: function (this:G, ?, ?): undefined");
  }