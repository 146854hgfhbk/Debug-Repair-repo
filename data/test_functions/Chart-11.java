    public void testEqualGeneralPaths() {
        GeneralPath g1 = new GeneralPath();
        g1.moveTo(1.0f, 2.0f);
        g1.lineTo(3.0f, 4.0f);
        g1.curveTo(5.0f, 6.0f, 7.0f, 8.0f, 9.0f, 10.0f);
        g1.quadTo(1.0f, 2.0f, 3.0f, 4.0f);
        g1.closePath();
        GeneralPath g2 = new GeneralPath();
        g2.moveTo(1.0f, 2.0f);
        g2.lineTo(3.0f, 4.0f);
        g2.curveTo(5.0f, 6.0f, 7.0f, 8.0f, 9.0f, 10.0f);
        g2.quadTo(1.0f, 2.0f, 3.0f, 4.0f);
        g2.closePath();
        assertTrue(ShapeUtilities.equal(g1, g2));

        g2 = new GeneralPath();
        g2.moveTo(11.0f, 22.0f);
        g2.lineTo(3.0f, 4.0f);
        g2.curveTo(5.0f, 6.0f, 7.0f, 8.0f, 9.0f, 10.0f);
        g2.quadTo(1.0f, 2.0f, 3.0f, 4.0f);
        g2.closePath();
        assertFalse(ShapeUtilities.equal(g1, g2));

        g2 = new GeneralPath();
        g2.moveTo(1.0f, 2.0f);
        g2.lineTo(33.0f, 44.0f);
        g2.curveTo(5.0f, 6.0f, 7.0f, 8.0f, 9.0f, 10.0f);
        g2.quadTo(1.0f, 2.0f, 3.0f, 4.0f);
        g2.closePath();
        assertFalse(ShapeUtilities.equal(g1, g2));

        g2 = new GeneralPath();
        g2.moveTo(1.0f, 2.0f);
        g2.lineTo(3.0f, 4.0f);
        g2.curveTo(55.0f, 66.0f, 77.0f, 88.0f, 99.0f, 100.0f);
        g2.quadTo(1.0f, 2.0f, 3.0f, 4.0f);
        g2.closePath();
        assertFalse(ShapeUtilities.equal(g1, g2));

        g2 = new GeneralPath();
        g2.moveTo(1.0f, 2.0f);
        g2.lineTo(3.0f, 4.0f);
        g2.curveTo(5.0f, 6.0f, 7.0f, 8.0f, 9.0f, 10.0f);
        g2.quadTo(11.0f, 22.0f, 33.0f, 44.0f);
        g2.closePath();
        assertFalse(ShapeUtilities.equal(g1, g2));

        g2 = new GeneralPath();
        g2.moveTo(1.0f, 2.0f);
        g2.lineTo(3.0f, 4.0f);
        g2.curveTo(5.0f, 6.0f, 7.0f, 8.0f, 9.0f, 10.0f);
        g2.quadTo(1.0f, 2.0f, 3.0f, 4.0f);
        g2.lineTo(3.0f, 4.0f);
        g2.closePath();
        assertFalse(ShapeUtilities.equal(g1, g2));
    }