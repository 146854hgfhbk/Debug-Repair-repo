  public void testStructuralConstructor2() throws Exception {
    JSType type = testParseType(
        "function (new:?)",
        // toString skips unknowns, but isConstructor reveals the truth.
        "function (): ?");
    assertTrue(type.isConstructor());
    assertFalse(type.isNominalConstructor());
  }