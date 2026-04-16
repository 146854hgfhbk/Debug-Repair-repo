  public void testIssue779() {
    testNotMissing(
        "var a = f(); try { alert(); if (a > 0) return 1; }" +
        "finally { a = 5; } return 2;");
  }