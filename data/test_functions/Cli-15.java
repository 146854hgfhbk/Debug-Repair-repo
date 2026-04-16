    public void testSingleOptionSingleArgument() throws Exception {
        Parser parser = createDefaultValueParser(new String[]{"100", "1000"});
        String enteredValue1 = "1";
        String[] args = new String[]{"-b", enteredValue1};
        CommandLine cl = parser.parse(args);
        CommandLine cmd = cl;
        assertNotNull(cmd);
        List b = cmd.getValues("-b");
        assertEquals("[" + enteredValue1 + ", 1000]", b + "");
    }