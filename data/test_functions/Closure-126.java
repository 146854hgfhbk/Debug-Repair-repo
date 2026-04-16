  public void testDontRemoveBreakInTryFinally() throws Exception {
    foldSame("function f() {b:try{throw 9} finally {break b} return 1;}");
  }