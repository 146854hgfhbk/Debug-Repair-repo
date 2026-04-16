    public void testExtremeValues() throws Exception {
        NormalDistribution distribution = (NormalDistribution) getDistribution();
        distribution.setMean(0);
        distribution.setStandardDeviation(1);
        for (int i = 0; i < 100; i+=5) { // make sure no convergence exception
            double lowerTail = distribution.cumulativeProbability((double)-i);
            double upperTail = distribution.cumulativeProbability((double) i);
            if (i < 10) { // make sure not top-coded
                assertTrue(lowerTail > 0.0d);
                assertTrue(upperTail < 1.0d);
            }
            else { // make sure top coding not reversed
                assertTrue(lowerTail < 0.00001);
                assertTrue(upperTail > 0.99999);
            }
        } 
   }