    public void testAddNonComparable(){
        try {
            f.addValue(new Object()); // This was OK
            fail("Expected ClassCastException");
        } catch (ClassCastException expected) {
        }
        f.clear();
        f.addValue(1);
        try {
            f.addValue(new Object());
            fail("Expected ClassCastException"); // Previously would have been IllegalArgument
        } catch (ClassCastException expected) {
        }
    }