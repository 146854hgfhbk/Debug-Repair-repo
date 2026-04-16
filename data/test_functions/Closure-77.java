  public void testZero() {
    assertPrint("var x ='\\0';", "var x=\"\\0\"");
    assertPrint("var x ='\\x00';", "var x=\"\\0\"");
    assertPrint("var x ='\\u0000';", "var x=\"\\0\"");
  }