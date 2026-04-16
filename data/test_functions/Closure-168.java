  public void testIssue726() throws Exception {
    testTypes(
        "/** @constructor */ function Foo() {}" +
        "/** @param {number} x */ Foo.prototype.bar = function(x) {};" +
        "/** @return {!Function} */ " +
        "Foo.prototype.getDeferredBar = function() { " +
        "  var self = this;" +
        "  return function() {" +
        "    self.bar(true);" +
        "  };" +
        "};",
        "actual parameter 1 of Foo.prototype.bar does not match formal parameter\n" +
        "found   : boolean\n" +
        "required: number");
  }