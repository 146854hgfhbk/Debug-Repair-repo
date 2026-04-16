  public void testRecursiveTypeVariablesResolve12() throws Exception {
    TypeAdapter<TestType2> adapter = new Gson().getAdapter(TestType2.class);
    assertNotNull(adapter);
  }