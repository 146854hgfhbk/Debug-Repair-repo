  public void testImplementsExtendsLoop() throws Exception {
    testClosureTypesMultipleWarnings(
        suppressMissingProperty("foo") +
            "/** @constructor \n * @implements {F} */var G = function() {};" +
            "/** @constructor \n * @extends {G} */var F = function() {};" +
        "alert((new F).foo);",
        Lists.newArrayList(
            "Parse error. Cycle detected in inheritance chain of type F"));
  }