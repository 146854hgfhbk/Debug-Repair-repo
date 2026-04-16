    public void testPValueNearZero() throws Exception {
        /*
         * Create a dataset that has r -> 1, p -> 0 as dimension increases.
         * Prior to the fix for MATH-371, p vanished for dimension >= 14.
         * Post fix, p-values diminish smoothly, vanishing at dimension = 127.
         * Tested value is ~1E-303.
         */
        int dimension = 120; 
        double[][] data = new double[dimension][2];
        for (int i = 0; i < dimension; i++) {
            data[i][0] = i;
            data[i][1] = i + 1/((double)i + 1);
        }
        PearsonsCorrelation corrInstance = new PearsonsCorrelation(data);
        assertTrue(corrInstance.getCorrelationPValues().getEntry(0, 1) > 0);
    }