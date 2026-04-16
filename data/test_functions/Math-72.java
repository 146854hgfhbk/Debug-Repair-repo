    public void testRootEndpoints() throws Exception {
        UnivariateRealFunction f = new SinFunction();
        UnivariateRealSolver solver = new BrentSolver();

        // endpoint is root
        double result = solver.solve(f, Math.PI, 4);
        assertEquals(Math.PI, result, solver.getAbsoluteAccuracy());

        result = solver.solve(f, 3, Math.PI);
        assertEquals(Math.PI, result, solver.getAbsoluteAccuracy());

        result = solver.solve(f, Math.PI, 4, 3.5);
        assertEquals(Math.PI, result, solver.getAbsoluteAccuracy());

        result = solver.solve(f, 3, Math.PI, 3.07);
        assertEquals(Math.PI, result, solver.getAbsoluteAccuracy());

    }