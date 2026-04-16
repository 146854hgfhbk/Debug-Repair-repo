    public void testUnfinishedEntity() {
        NumericEntityUnescaper neu = new NumericEntityUnescaper();
        String input = "Test &#x30 not test";
        String expected = "Test \u0030 not test";

        String result = neu.translate(input);
        assertEquals("Failed to support unfinished entities (i.e. missing semi-colon", expected, result);
    }