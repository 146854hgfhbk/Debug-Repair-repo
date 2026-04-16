    public void testLANG807() {
        try {
            RandomStringUtils.random(3,5,5,false,false);
            fail("Expected IllegalArgumentException");
        } catch (IllegalArgumentException ex) { // distinguish from Random#nextInt message
            final String msg = ex.getMessage();
            assertTrue("Message (" + msg + ") must contain 'start'", msg.contains("start"));
            assertTrue("Message (" + msg + ") must contain 'end'", msg.contains("end"));
        }
    }