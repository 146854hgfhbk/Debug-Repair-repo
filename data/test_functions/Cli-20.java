    public void testStop3() throws Exception
    {
        String[] args = new String[]{"--zop==1",
                                     "-abtoast",
                                     "--b=bar"};

        CommandLine cl = parser.parse(options, args, true);

        assertFalse("Confirm -a is not set", cl.hasOption("a"));
        assertFalse("Confirm -b is not set", cl.hasOption("b"));
        assertTrue("Confirm  3 extra args: " + cl.getArgList().size(), cl.getArgList().size() == 3);
    }