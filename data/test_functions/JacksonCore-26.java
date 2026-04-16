    public void testLocationOffsets() throws Exception
    {
        JsonParser parser = DEFAULT_F.createNonBlockingByteArrayParser();
        ByteArrayFeeder feeder = (ByteArrayFeeder) parser.getNonBlockingInputFeeder();

        byte[] input = utf8Bytes("[[[");

        feeder.feedInput(input, 2, 3);
        assertEquals(JsonToken.START_ARRAY, parser.nextToken());
        assertEquals(1, parser.getCurrentLocation().getByteOffset());
        assertEquals(1, parser.getTokenLocation().getByteOffset());
        assertEquals(1, parser.getCurrentLocation().getLineNr());
        assertEquals(1, parser.getTokenLocation().getLineNr());
        assertEquals(2, parser.getCurrentLocation().getColumnNr());
        assertEquals(1, parser.getTokenLocation().getColumnNr());

        feeder.feedInput(input, 0, 1);
        assertEquals(JsonToken.START_ARRAY, parser.nextToken());
        assertEquals(2, parser.getCurrentLocation().getByteOffset());
        assertEquals(2, parser.getTokenLocation().getByteOffset());
        assertEquals(1, parser.getCurrentLocation().getLineNr());
        assertEquals(1, parser.getTokenLocation().getLineNr());
        assertEquals(3, parser.getCurrentLocation().getColumnNr());
        assertEquals(2, parser.getTokenLocation().getColumnNr());
        parser.close();
    }