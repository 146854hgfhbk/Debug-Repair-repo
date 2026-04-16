    public void testExceptions() {
        final char[] DUMMY = new char[]{'a'}; // valid char array
        try {
            RandomStringUtils.random(-1);
            fail();
        } catch (IllegalArgumentException ex) {}
        try {
            RandomStringUtils.random(-1, true, true);
            fail();
        } catch (IllegalArgumentException ex) {}
        try {
            RandomStringUtils.random(-1, DUMMY);
            fail();
        } catch (IllegalArgumentException ex) {}
        try {
            RandomStringUtils.random(1, new char[0]); // must not provide empty array => IAE
            fail();
        } catch (IllegalArgumentException ex) {}
        try {
            RandomStringUtils.random(-1, "");
            fail();
        } catch (IllegalArgumentException ex) {}
        try {
            RandomStringUtils.random(-1, (String)null);
            fail();
        } catch (IllegalArgumentException ex) {}
        try {
            RandomStringUtils.random(-1, 'a', 'z', false, false);
            fail();
        } catch (IllegalArgumentException ex) {}
        try {
            RandomStringUtils.random(-1, 'a', 'z', false, false, DUMMY);
            fail();
        } catch (IllegalArgumentException ex) {}
        try {
            RandomStringUtils.random(-1, 'a', 'z', false, false, DUMMY, new Random());
            fail();
        } catch (IllegalArgumentException ex) {}
    }