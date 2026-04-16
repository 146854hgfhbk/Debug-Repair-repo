    public void testSqlDateConfigOverride() throws Exception
    {
        ObjectMapper mapper = newObjectMapper();
        mapper.configOverride(java.sql.Date.class)
            .setFormat(JsonFormat.Value.forPattern("yyyy+MM+dd"));        
        assertEquals("\"1980+04+14\"",
            mapper.writeValueAsString(java.sql.Date.valueOf("1980-04-14")));
    }