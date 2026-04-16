    public void testMath789() {

        final RealMatrix m1 = MatrixUtils.createRealMatrix(new double[][]{
            {0.013445532, 0.010394690, 0.009881156, 0.010499559},
            {0.010394690, 0.023006616, 0.008196856, 0.010732709},
            {0.009881156, 0.008196856, 0.019023866, 0.009210099},
            {0.010499559, 0.010732709, 0.009210099, 0.019107243}
        });
        RealMatrix root1 = new RectangularCholeskyDecomposition(m1, 1.0e-10).getRootMatrix();
        RealMatrix rebuiltM1 = root1.multiply(root1.transpose());
        Assert.assertEquals(0.0, m1.subtract(rebuiltM1).getNorm(), 1.0e-16);

        final RealMatrix m2 = MatrixUtils.createRealMatrix(new double[][]{
            {0.0, 0.0, 0.0, 0.0, 0.0},
            {0.0, 0.013445532, 0.010394690, 0.009881156, 0.010499559},
            {0.0, 0.010394690, 0.023006616, 0.008196856, 0.010732709},
            {0.0, 0.009881156, 0.008196856, 0.019023866, 0.009210099},
            {0.0, 0.010499559, 0.010732709, 0.009210099, 0.019107243}
        });
        RealMatrix root2 = new RectangularCholeskyDecomposition(m2, 1.0e-10).getRootMatrix();
        RealMatrix rebuiltM2 = root2.multiply(root2.transpose());
        Assert.assertEquals(0.0, m2.subtract(rebuiltM2).getNorm(), 1.0e-16);

        final RealMatrix m3 = MatrixUtils.createRealMatrix(new double[][]{
            {0.013445532, 0.010394690, 0.0, 0.009881156, 0.010499559},
            {0.010394690, 0.023006616, 0.0, 0.008196856, 0.010732709},
            {0.0, 0.0, 0.0, 0.0, 0.0},
            {0.009881156, 0.008196856, 0.0, 0.019023866, 0.009210099},
            {0.010499559, 0.010732709, 0.0, 0.009210099, 0.019107243}
        });
        RealMatrix root3 = new RectangularCholeskyDecomposition(m3, 1.0e-10).getRootMatrix();
        RealMatrix rebuiltM3 = root3.multiply(root3.transpose());
        Assert.assertEquals(0.0, m3.subtract(rebuiltM3).getNorm(), 1.0e-16);

    }