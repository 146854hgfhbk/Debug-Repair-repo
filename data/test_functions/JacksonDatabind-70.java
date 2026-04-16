    public void testCaseInsensitiveUnwrap() throws Exception
    {
        ObjectMapper mapper = new ObjectMapper();
        mapper.enable(MapperFeature.ACCEPT_CASE_INSENSITIVE_PROPERTIES);
        Person p = mapper.readValue("{ }", Person.class);
        assertNotNull(p);
    }