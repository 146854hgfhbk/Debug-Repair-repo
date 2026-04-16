    public void testAbbreviate() {
        // check null and empty are returned respectively
        assertNull(WordUtils.abbreviate(null, 1,-1,""));
        assertEquals(StringUtils.EMPTY, WordUtils.abbreviate("", 1,-1,""));

        // test upper limit
        assertEquals("01234", WordUtils.abbreviate("0123456789", 0,5,""));
        assertEquals("01234", WordUtils.abbreviate("0123456789", 5, 2,""));
        assertEquals("012", WordUtils.abbreviate("012 3456789", 2, 5,""));
        assertEquals("012 3", WordUtils.abbreviate("012 3456789", 5, 2,""));
        assertEquals("0123456789", WordUtils.abbreviate("0123456789", 0,-1,""));

        // test upper limit + append string
        assertEquals("01234-", WordUtils.abbreviate("0123456789", 0,5,"-"));
        assertEquals("01234-", WordUtils.abbreviate("0123456789", 5, 2,"-"));
        assertEquals("012", WordUtils.abbreviate("012 3456789", 2, 5, null));
        assertEquals("012 3", WordUtils.abbreviate("012 3456789", 5, 2,""));
        assertEquals("0123456789", WordUtils.abbreviate("0123456789", 0,-1,""));

        // test lower value
        assertEquals("012", WordUtils.abbreviate("012 3456789", 0,5, null));
        assertEquals("01234", WordUtils.abbreviate("01234 56789", 5, 10, null));
        assertEquals("01 23 45 67", WordUtils.abbreviate("01 23 45 67 89", 9, -1, null));
        assertEquals("01 23 45 6", WordUtils.abbreviate("01 23 45 67 89", 9, 10, null));
        assertEquals("0123456789", WordUtils.abbreviate("0123456789", 15, 20, null));

        // test lower value + append
        assertEquals("012", WordUtils.abbreviate("012 3456789", 0,5, null));
        assertEquals("01234-", WordUtils.abbreviate("01234 56789", 5, 10, "-"));
        assertEquals("01 23 45 67abc", WordUtils.abbreviate("01 23 45 67 89", 9, -1, "abc"));
        assertEquals("01 23 45 6", WordUtils.abbreviate("01 23 45 67 89", 9, 10, ""));

        // others
        assertEquals("", WordUtils.abbreviate("0123456790", 0,0,""));
        assertEquals("", WordUtils.abbreviate(" 0123456790", 0,-1,""));
    }