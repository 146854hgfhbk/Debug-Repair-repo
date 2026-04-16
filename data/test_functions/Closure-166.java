  public void testRecordInference() {
    inFunction(
        "/** @param {{a: (boolean|undefined)}|{b: (string|undefined)}} x */" +
        "function f(x) {}" +
        "var out = {};" +
        "f(out);");
    assertEquals("{a: (boolean|undefined), b: (string|undefined)}",
        getType("out").toString());
  }