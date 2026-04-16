    public void testBinaryAsEmbeddedObject() throws Exception
    {
        JsonGenerator g;

        StringWriter sw = new StringWriter();
        g = JSON_F.createGenerator(sw);
        g.writeEmbeddedObject(WIKIPEDIA_BASE64_AS_BYTES);
        g.close();
        assertEquals(quote(WIKIPEDIA_BASE64_ENCODED), sw.toString());

        ByteArrayOutputStream bytes =  new ByteArrayOutputStream(100);
        g = JSON_F.createGenerator(bytes);
        g.writeEmbeddedObject(WIKIPEDIA_BASE64_AS_BYTES);
        g.close();
        assertEquals(quote(WIKIPEDIA_BASE64_ENCODED), bytes.toString("UTF-8"));
    }