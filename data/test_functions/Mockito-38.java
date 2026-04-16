    public void shouldWorkFineWhenGivenArgIsNull() {
        //when
        Integer[] suspicious = tool.getSuspiciouslyNotMatchingArgsIndexes((List) Arrays.asList(new Equals(20)), new Object[] {null});
        
        //then
        assertEquals(0, suspicious.length);
    }