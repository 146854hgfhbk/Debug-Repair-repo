    public void testDateTimeCreation_london() {
        DateTimeZone zone = DateTimeZone.forID("Europe/London");
        DateTime base = new DateTime(2011, 10, 30, 1, 15, zone);
        assertEquals("2011-10-30T01:15:00.000+01:00", base.toString());
        assertEquals("2011-10-30T01:15:00.000Z", base.plusHours(1).toString());
    }