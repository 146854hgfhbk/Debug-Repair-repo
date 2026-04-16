    public void survivesBlankLinesInPaxHeader() throws Exception {
        final TarArchiveInputStream is = getTestStream("/COMPRESS-355.tar");
        try {
            final TarArchiveEntry entry = is.getNextTarEntry();
            assertEquals("package/package.json", entry.getName());
            assertNull(is.getNextTarEntry());
        } finally {
            is.close();
        }
    }