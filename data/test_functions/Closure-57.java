  public void testRequire() {
    assertRequire("goog.require('foo')");
    assertNotRequire("goog.require(foo)");
    assertNotRequire("goog.require()");
    assertNotRequire("foo()");
  }