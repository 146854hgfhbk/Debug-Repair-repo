    @Test(expected = IllegalArgumentException.class) public void validatesKeysNotEmpty() {
        Attribute attr = new Attribute(" ", "Check");
    }