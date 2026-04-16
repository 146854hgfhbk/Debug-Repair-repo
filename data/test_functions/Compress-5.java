    public void testRead7ZipMultiVolumeArchiveForStream() throws IOException,
	    URISyntaxException {
	
	URL zip = getClass().getResource("/apache-maven-2.2.1.zip.001");
	FileInputStream archive = new FileInputStream(
		new File(new URI(zip.toString())));
	ZipArchiveInputStream zi = null;
	try {
	    zi = new ZipArchiveInputStream(archive,null,false);
	    
	    // these are the entries that are supposed to be processed
	    // correctly without any problems
	    for (int i = 0; i < ENTRIES.length; i++) {
		assertEquals(ENTRIES[i], zi.getNextEntry().getName());
	    }
	    
	    // this is the last entry that is truncated
	    ArchiveEntry lastEntry = zi.getNextEntry();
	    assertEquals(LAST_ENTRY_NAME, lastEntry.getName());
	    byte [] buffer = new byte [4096];
	    
	    // before the fix, we'd get 0 bytes on this read and all
	    // subsequent reads thus a client application might enter
	    // an infinite loop after the fix, we should get an
	    // exception
	    try {
                int read = 0;
		while ((read = zi.read(buffer)) > 0) { }
		fail("shouldn't be able to read from truncated entry");
	    } catch (IOException e) {
                assertEquals("Truncated ZIP file", e.getMessage());
	    }
	    
	    // and now we get another entry, which should also yield
	    // an exception
	    try {
		zi.getNextEntry();
		fail("shouldn't be able to read another entry from truncated"
                     + " file");
	    } catch (IOException e) {
		// this is to be expected
	    }
	} finally {
	    if (zi != null) {
		zi.close();
	    }
	}
    }