  public void testIssue1101a() {
    helperCanInlineReferenceToFunction(CanInlineResult.NO,
        "function foo(a){return modifiyX() + a;} foo(x);", "foo",
        INLINE_DIRECT);
  }