    public void testBoundaryRangeTooLarge() {
        final CMAESOptimizer optimizer = new CMAESOptimizer();
        final MultivariateFunction fitnessFunction = new MultivariateFunction() {
                public double value(double[] parameters) {
                    if (Double.isNaN(parameters[0])) {
                        throw new MathIllegalStateException();
                    }
                    final double target = 1;
                    final double error = target - parameters[0];
                    return error * error;
                }
            };

        final double[] start = { 0 };

        // The difference between upper and lower bounds is used to used
        // normalize the variables: In case of overflow, NaN is produced.
        final double max = Double.MAX_VALUE / 2;
        final double tooLarge = FastMath.nextUp(max);
        final double[] lower = { -tooLarge };
        final double[] upper = { tooLarge };
        final double[] result = optimizer.optimize(10000, fitnessFunction, GoalType.MINIMIZE,
                                                   start, lower, upper).getPoint();
    }