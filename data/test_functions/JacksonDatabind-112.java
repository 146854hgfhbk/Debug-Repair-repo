    public void testDeserializeBagOfStrings() throws Exception {
        WithBagOfStrings result = MAPPER.readerFor(WithBagOfStrings.class)
                .readValue("{\"strings\": [ \"a\", \"b\", \"c\"]}");
        assertEquals(3, result.getStrings().size());
    }