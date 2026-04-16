    public void testWith3() {
        Partial test = createHourMinPartial();
        try {
            test.with(DateTimeFieldType.clockhourOfDay(), 6);
            fail();
        } catch (IllegalArgumentException ex) {}
        check(test, 10, 20);
    }