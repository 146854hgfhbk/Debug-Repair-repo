    public void testIssue941() throws Exception
    {
        ObjectNode object = MAPPER.createObjectNode();

        String json = MAPPER.writeValueAsString(object);
        System.out.println("json: "+json);

        ObjectNode de1 = MAPPER.readValue(json, ObjectNode.class);  // this works
        System.out.println("Deserialized to ObjectNode: "+de1);

        MyValue de2 = MAPPER.readValue(json, MyValue.class);  // but this throws exception
        System.out.println("Deserialized to MyValue: "+de2);
    }