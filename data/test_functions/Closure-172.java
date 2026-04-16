  public void testIssue1024() throws Exception {
     testTypes(
        "/** @param {Object} a */\n" +
        "function f(a) {\n" +
        "  a.prototype = '__proto'\n" +
        "}\n" +
        "/** @param {Object} b\n" +
        " *  @return {!Object}\n" +
        " */\n" +
        "function g(b) {\n" +
        "  return b.prototype\n" +
        "}\n");
     /* TODO(blickly): Make this warning go away.
      * This is old behavior, but it doesn't make sense to warn about since
      * both assignments are inferred.
      */
     testTypes(
        "/** @param {Object} a */\n" +
        "function f(a) {\n" +
        "  a.prototype = {foo:3};\n" +
        "}\n" +
        "/** @param {Object} b\n" +
        " */\n" +
        "function g(b) {\n" +
        "  b.prototype = function(){};\n" +
        "}\n",
        "assignment to property prototype of Object\n" +
        "found   : {foo: number}\n" +
        "required: function (): undefined");
  }