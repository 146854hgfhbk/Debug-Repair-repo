  public void testSuspiciousBlockCommentWarning3() {
    parse("/* \n *@type {number} */ var x = 3;", SUSPICIOUS_COMMENT_WARNING);
  }