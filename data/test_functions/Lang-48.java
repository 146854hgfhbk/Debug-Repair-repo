    public void testBigDecimal() {
        BigDecimal o1 = new BigDecimal("2.0");
        BigDecimal o2 = new BigDecimal("2.00");
        assertTrue(new EqualsBuilder().append(o1, o1).isEquals());
        assertTrue(new EqualsBuilder().append(o1, o2).isEquals());
    }