    public void testCompress197() throws Exception {
        TarArchiveInputStream tar = getTestStream("/COMPRESS-197.tar");
        try {
            TarArchiveEntry entry = tar.getNextTarEntry();
            while (entry != null) {
                entry = tar.getNextTarEntry();
            }
        } catch (IOException e) {
            fail("COMPRESS-197: " + e.getMessage());
        } finally {
            tar.close();
        }
    }