    public void testMath844() {
        final double[] y = { 0, 1, 2, 3, 2, 1,
                             0, -1, -2, -3, -2, -1,
                             0, 1, 2, 3, 2, 1,
                             0, -1, -2, -3, -2, -1,
                             0, 1, 2, 3, 2, 1, 0 };
        final int len = y.length;
        final WeightedObservedPoint[] points = new WeightedObservedPoint[len];
        for (int i = 0; i < len; i++) {
            points[i] = new WeightedObservedPoint(1, i, y[i]);
        }

        final HarmonicFitter.ParameterGuesser guesser
            = new HarmonicFitter.ParameterGuesser(points);

        // The guesser fails because the function is far from an harmonic
        // function: It is a triangular periodic function with amplitude 3
        // and period 12, and all sample points are taken at integer abscissae
        // so function values all belong to the integer subset {-3, -2, -1, 0,
        // 1, 2, 3}.
        guesser.guess();
    }