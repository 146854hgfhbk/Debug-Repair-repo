    public void readEntriesOfSize0() throws IOException {
        final SevenZFile sevenZFile = new SevenZFile(getFile("COMPRESS-348.7z"));
        try {
            int entries = 0;
            SevenZArchiveEntry entry = sevenZFile.getNextEntry();
            while (entry != null) {
                entries++;
                int b = sevenZFile.read();
                if ("2.txt".equals(entry.getName()) || "5.txt".equals(entry.getName())) {
                    assertEquals(-1, b);
                } else {
                    assertNotEquals(-1, b);
                }
                entry = sevenZFile.getNextEntry();
            }
            assertEquals(5, entries);
        } finally {
            sevenZFile.close();
        }
    }