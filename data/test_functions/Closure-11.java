  public void testGetprop4() throws Exception {
    testTypes("var x = null; x.prop = 3;",
        "No properties on this expression\n" +
        "found   : null\n" +
        "required: Object");
  }