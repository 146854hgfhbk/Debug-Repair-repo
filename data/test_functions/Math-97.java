    public void testRootEndpoints() throws Exception {
        UnivariateRealFunction f = new SinFunction();
        UnivariateRealSolver solver = new BrentSolver(f);
        
        // endpoint is root
        double result = solver.solve(Math.PI, 4);
        assertEquals(result, Math.PI, solver.getAbsoluteAccuracy());

        result = solver.solve(3, Math.PI);
        assertEquals(result, Math.PI, solver.getAbsoluteAccuracy());
    }