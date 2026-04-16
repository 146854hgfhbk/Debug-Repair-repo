    public void consumeToNonexistentEndWhenAtAnd() {
        CharacterReader r = new CharacterReader("<!");
        assertTrue(r.matchConsume("<!"));
        assertTrue(r.isEmpty());

        String after = r.consumeTo('>');
        assertEquals("", after);

        assertTrue(r.isEmpty());
    }