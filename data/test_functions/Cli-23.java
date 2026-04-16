    public void testInfiniteLoop() {
        HelpFormatter formatter = new HelpFormatter();
        formatter.setWidth(20);
        formatter.printHelp("app", options); // used to hang & crash
    }