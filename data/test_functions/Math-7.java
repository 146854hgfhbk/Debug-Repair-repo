  public void testEventsScheduling() {

      FirstOrderDifferentialEquations sincos = new FirstOrderDifferentialEquations() {

          public int getDimension() {
              return 2;
          }

          public void computeDerivatives(double t, double[] y, double[] yDot) {
              yDot[0] =  y[1];
              yDot[1] = -y[0];
          }

      };

      SchedulingChecker sinChecker = new SchedulingChecker(0); // events at 0, PI, 2PI ...
      SchedulingChecker cosChecker = new SchedulingChecker(1); // events at PI/2, 3PI/2, 5PI/2 ...

      FirstOrderIntegrator integ =
              new DormandPrince853Integrator(0.001, 1.0, 1.0e-12, 0.0);
      integ.addEventHandler(sinChecker, 0.01, 1.0e-7, 100);
      integ.addStepHandler(sinChecker);
      integ.addEventHandler(cosChecker, 0.01, 1.0e-7, 100);
      integ.addStepHandler(cosChecker);
      double   t0 = 0.5;
      double[] y0 = new double[] { FastMath.sin(t0), FastMath.cos(t0) };
      double   t  = 10.0;
      double[] y  = new double[2];
      integ.integrate(sincos, t0, y0, t, y);

  }