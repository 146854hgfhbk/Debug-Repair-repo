    public void testCachedSerialize() throws IOException {
        ObjectMapper mapper = new ObjectMapper();
        String json = aposToQuotes("{'data':{'1st':'onedata','2nd':'twodata'}}");

        // Do deserialization with non-annotated map property
        NonAnnotatedMapHolderClass ignored = mapper.readValue(json, NonAnnotatedMapHolderClass.class);
        assertTrue(ignored.data.containsKey("1st"));
        assertTrue(ignored.data.containsKey("2nd"));

//mapper = new ObjectMapper();
        
        MapHolder model2 = mapper.readValue(json, MapHolder.class);
        if (!model2.data.containsKey("1st (CUSTOM)")
            || !model2.data.containsKey("2nd (CUSTOM)")) {
            fail("Not using custom key deserializer for input: "+json+"; resulted in: "+model2.data);
        }
    }