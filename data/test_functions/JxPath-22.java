    public void testInnerEmptyNamespaceDOM() {
        doTest("b:foo/test", DocumentContainer.MODEL_DOM, "/b:foo[1]/test[1]");
    }