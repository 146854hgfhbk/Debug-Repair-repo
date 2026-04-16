  public void testNegativeZero() throws Exception {
	  	JsonReader reader = new JsonReader(reader("[-0]"));
	    reader.setLenient(false);
	    reader.beginArray();
	    assertEquals(NUMBER, reader.peek());
	    assertEquals("-0", reader.nextString());
  }