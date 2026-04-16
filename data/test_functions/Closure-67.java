  public void testAliasing7() {
    // An exported alias must preserved any referenced values in the
    // referenced function.
    testSame("function e(){}" +
           "e.prototype['alias1'] = e.prototype.method1 = " +
               "function(){this.method2()};" +
           "e.prototype.method2 = function(){};");
  }