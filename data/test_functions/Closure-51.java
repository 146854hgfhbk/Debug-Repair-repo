  public void testIssue582() {
    assertPrint("var x = -0.0;", "var x=-0.0");
  }