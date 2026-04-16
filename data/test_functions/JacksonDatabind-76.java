    public void testWithUnwrappedAndCreatorSingleParameterAtBeginning() throws Exception {
        final String json = aposToQuotes("{'person_id':1234,'first_name':'John','last_name':'Doe','years_old':30,'living':true}");

        final ObjectMapper mapper = new ObjectMapper();
        Person person = mapper.readValue(json, Person.class);
        assertEquals(1234, person.getId());
        assertNotNull(person.getName());
        assertEquals("John", person.getName().getFirst());
        assertEquals("Doe", person.getName().getLast());
        assertEquals(30, person.getAge());
        assertEquals(true, person.isAlive());
    }