    public void testEquals() {
        final CharSequence fooCs = FOO, barCs = BAR, foobarCs = FOOBAR;
        assertTrue(StringUtils.equals(null, null));
        assertTrue(StringUtils.equals(fooCs, fooCs));
        assertTrue(StringUtils.equals(fooCs, (CharSequence) new StringBuilder(FOO)));
        assertTrue(StringUtils.equals(fooCs, (CharSequence) new String(new char[] { 'f', 'o', 'o' })));
        assertTrue(StringUtils.equals(fooCs, (CharSequence) new CustomCharSequence(FOO)));
        assertTrue(StringUtils.equals((CharSequence) new CustomCharSequence(FOO), fooCs));
        assertFalse(StringUtils.equals(fooCs, (CharSequence) new String(new char[] { 'f', 'O', 'O' })));
        assertFalse(StringUtils.equals(fooCs, barCs));
        assertFalse(StringUtils.equals(fooCs, null));
        assertFalse(StringUtils.equals(null, fooCs));
        assertFalse(StringUtils.equals(fooCs, foobarCs));
        assertFalse(StringUtils.equals(foobarCs, fooCs));
    }