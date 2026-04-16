    public void testDoubleMetaphoneAlternate() {
        String value = null;
        for (int i = 0; i < TEST_DATA.length; i++) {
            value = TEST_DATA[i][0];
            assertEquals("Test [" + i + "]=" + value, TEST_DATA[i][2], doubleMetaphone.doubleMetaphone(value, true));
        }
    }