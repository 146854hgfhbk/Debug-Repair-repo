  public void testBug545() {
    testLocal("var a = {}", "");
    testLocal("var a; a = {}", "true");
  }