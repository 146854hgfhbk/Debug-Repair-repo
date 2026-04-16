    public void aiffFilesAreNoTARs() throws Exception {
        InputStream is = null;
        try {
            is = new BufferedInputStream(new FileInputStream("src/test/resources/testAIFF.aif"));
            new ArchiveStreamFactory().createArchiveInputStream(is);
            fail("created an input stream for a non-archive");
        } catch (ArchiveException ae) {
            assertTrue(ae.getMessage().startsWith("No Archiver found"));
        } finally {
            if (is != null) {
                is.close();
            }
        }
    }