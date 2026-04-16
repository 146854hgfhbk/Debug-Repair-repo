    public void testBuilderIsResettedAlways() {
        try
        {
            OptionBuilder.withDescription("JUnit").create('"');
            fail("IllegalArgumentException expected");
        }
        catch (IllegalArgumentException e)
        {
            // expected
        }
        assertNull("we inherited a description", OptionBuilder.create('x').getDescription());

        try
        {
            OptionBuilder.withDescription("JUnit").create();
            fail("IllegalArgumentException expected");
        }
        catch (IllegalArgumentException e)
        {
            // expected
        }
        assertNull("we inherited a description", OptionBuilder.create('x').getDescription());
    }