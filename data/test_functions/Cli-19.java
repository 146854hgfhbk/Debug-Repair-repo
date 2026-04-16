    public void testUnrecognizedOption2() throws Exception
    {
        String[] args = new String[] { "-z", "-abtoast", "foo", "bar" };

        try
        {
            parser.parse(options, args);
            fail("UnrecognizedOptionException wasn't thrown");
        }
        catch (UnrecognizedOptionException e)
        {
            assertEquals("-z", e.getOption());
        }
    }