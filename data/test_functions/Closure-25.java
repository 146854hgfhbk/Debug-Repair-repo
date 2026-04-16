  public void testBackwardsInferenceNew() {
    inFunction(
        "/**\n" +
        " * @constructor\n" +
        " * @param {{foo: (number|undefined)}} x\n" +
        " */" +
        "function F(x) {}" +
        "var y = {};" +
        "new F(y);");

    assertEquals("{foo: (number|undefined)}", getType("y").toString());
  }