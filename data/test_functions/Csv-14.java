    public void testEscapeNull1() throws IOException {
        StringWriter sw = new StringWriter();
        try (final CSVPrinter printer = new CSVPrinter(sw, CSVFormat.DEFAULT.withEscape(null))) {
            printer.print("\\");
        }
        assertEquals("\\", sw.toString());
    }