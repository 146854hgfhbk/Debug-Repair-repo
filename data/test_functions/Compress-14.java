    public void workaroundForBrokenTimeHeader() throws Exception {
        URL tar = getClass().getResource("/simple-aix-native-tar.tar");
        TarArchiveInputStream in = null;
        try {
            in = new TarArchiveInputStream(new FileInputStream(new File(new URI(tar.toString()))));
            TarArchiveEntry tae = in.getNextTarEntry();
            tae = in.getNextTarEntry();
            assertEquals("sample/link-to-txt-file.lnk", tae.getName());
            assertEquals(new Date(0), tae.getLastModifiedDate());
            assertTrue(tae.isSymbolicLink());
        } finally {
            if (in != null) {
                in.close();
            }
        }
    }        