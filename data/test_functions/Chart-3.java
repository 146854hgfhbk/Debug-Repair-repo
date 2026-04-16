    public void testCreateCopy3() throws CloneNotSupportedException {
        TimeSeries s1 = new TimeSeries("S1");
        s1.add(new Year(2009), 100.0);
        s1.add(new Year(2010), 101.0);
        s1.add(new Year(2011), 102.0);
        assertEquals(100.0, s1.getMinY(), EPSILON);
        assertEquals(102.0, s1.getMaxY(), EPSILON);

        TimeSeries s2 = s1.createCopy(0, 1);
        assertEquals(100.0, s2.getMinY(), EPSILON);
        assertEquals(101.0, s2.getMaxY(), EPSILON);

        TimeSeries s3 = s1.createCopy(1, 2);
        assertEquals(101.0, s3.getMinY(), EPSILON);
        assertEquals(102.0, s3.getMaxY(), EPSILON);
    }