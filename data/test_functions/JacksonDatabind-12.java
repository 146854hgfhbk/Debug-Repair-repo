    public void testCustomMapValueDeser735() throws Exception {
        String json = "{\"map1\":{\"a\":1},\"map2\":{\"a\":1}}";
        TestMapBean735 bean = MAPPER.readValue(json, TestMapBean735.class);

        assertEquals(100, bean.map1.get("a").intValue());
        assertEquals(1, bean.map2.get("a").intValue());
    }