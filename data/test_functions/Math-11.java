    public void testUnivariateDistribution() {
        final double[] mu = { -1.5 };
        final double[][] sigma = { { 1 } };
 
        final MultivariateNormalDistribution multi = new MultivariateNormalDistribution(mu, sigma);

        final NormalDistribution uni = new NormalDistribution(mu[0], sigma[0][0]);
        final Random rng = new Random();
        final int numCases = 100;
        final double tol = Math.ulp(1d);
        for (int i = 0; i < numCases; i++) {
            final double v = rng.nextDouble() * 10 - 5;
            Assert.assertEquals(uni.density(v), multi.density(new double[] { v }), tol);
        }
    }