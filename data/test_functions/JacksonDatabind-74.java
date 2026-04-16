    public void testWithEmptyStringAsNullObject1533() throws Exception
    {
        ObjectMapper mapper = new ObjectMapper().enable(DeserializationFeature.ACCEPT_EMPTY_STRING_AS_NULL_OBJECT);
        AsPropertyWrapper wrapper = mapper.readValue("{ \"value\": \"\" }", AsPropertyWrapper.class);
        assertNull(wrapper.value);
    }