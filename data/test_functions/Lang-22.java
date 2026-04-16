    public void testReducedFactory_int_int() {
        Fraction f = null;
        
        // zero
        f = Fraction.getReducedFraction(0, 1);
        assertEquals(0, f.getNumerator());
        assertEquals(1, f.getDenominator());
        
        // normal
        f = Fraction.getReducedFraction(1, 1);
        assertEquals(1, f.getNumerator());
        assertEquals(1, f.getDenominator());
        
        f = Fraction.getReducedFraction(2, 1);
        assertEquals(2, f.getNumerator());
        assertEquals(1, f.getDenominator());
        
        // improper
        f = Fraction.getReducedFraction(22, 7);
        assertEquals(22, f.getNumerator());
        assertEquals(7, f.getDenominator());
        
        // negatives
        f = Fraction.getReducedFraction(-6, 10);
        assertEquals(-3, f.getNumerator());
        assertEquals(5, f.getDenominator());
        
        f = Fraction.getReducedFraction(6, -10);
        assertEquals(-3, f.getNumerator());
        assertEquals(5, f.getDenominator());
        
        f = Fraction.getReducedFraction(-6, -10);
        assertEquals(3, f.getNumerator());
        assertEquals(5, f.getDenominator());
        
        // zero denominator
        try {
            f = Fraction.getReducedFraction(1, 0);
            fail("expecting ArithmeticException");
        } catch (ArithmeticException ex) {}
        
        try {
            f = Fraction.getReducedFraction(2, 0);
            fail("expecting ArithmeticException");
        } catch (ArithmeticException ex) {}
        
        try {
            f = Fraction.getReducedFraction(-3, 0);
            fail("expecting ArithmeticException");
        } catch (ArithmeticException ex) {}

        // reduced        
        f = Fraction.getReducedFraction(0, 2);
        assertEquals(0, f.getNumerator());
        assertEquals(1, f.getDenominator());
        
        f = Fraction.getReducedFraction(2, 2);
        assertEquals(1, f.getNumerator());
        assertEquals(1, f.getDenominator());
        
        f = Fraction.getReducedFraction(2, 4);
        assertEquals(1, f.getNumerator());
        assertEquals(2, f.getDenominator());
        
        f = Fraction.getReducedFraction(15, 10);
        assertEquals(3, f.getNumerator());
        assertEquals(2, f.getDenominator());
        
        f = Fraction.getReducedFraction(121, 22);
        assertEquals(11, f.getNumerator());
        assertEquals(2, f.getDenominator());
        
        // Extreme values 
        // OK, can reduce before negating
        f = Fraction.getReducedFraction(-2, Integer.MIN_VALUE);
        assertEquals(1, f.getNumerator());
        assertEquals(-(Integer.MIN_VALUE / 2), f.getDenominator());
        
        // Can't reduce, negation will throw
        try { 
            f = Fraction.getReducedFraction(-7, Integer.MIN_VALUE);  
            fail("Expecting ArithmeticException");
        } catch (ArithmeticException ex) {}      

        // LANG-662
        f = Fraction.getReducedFraction(Integer.MIN_VALUE, 2);
        assertEquals(Integer.MIN_VALUE / 2, f.getNumerator());
        assertEquals(1, f.getDenominator());
    }