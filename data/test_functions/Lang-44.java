    public void testLang457() {
        String[] badInputs = new String[] { "l", "L", "f", "F", "junk", "bobL"};
        for(int i=0; i<badInputs.length; i++) {
            try {
                NumberUtils.createNumber(badInputs[i]);
                fail("NumberFormatException was expected for " + badInputs[i]);
            } catch (NumberFormatException e) {
                return; // expected
            }
        }
    }