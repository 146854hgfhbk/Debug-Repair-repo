    public void testIssue1351() throws Exception
    {
        ObjectMapper mapper = new ObjectMapper();
        mapper.setSerializationInclusion(JsonInclude.Include.NON_DEFAULT);
        assertEquals(aposToQuotes("{}"),
                mapper.writeValueAsString(new Issue1351Bean(null, (double) 0)));
        // [databind#1417]
        assertEquals(aposToQuotes("{}"),
                mapper.writeValueAsString(new Issue1351NonBean(0)));
    }