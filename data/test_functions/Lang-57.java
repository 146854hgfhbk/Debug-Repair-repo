    public void testAvailableLocaleSet() {
        Set set = LocaleUtils.availableLocaleSet();
        Set set2 = LocaleUtils.availableLocaleSet();
        assertNotNull(set);
        assertSame(set, set2);
        assertUnmodifiableCollection(set);
        
        Locale[] jdkLocaleArray = Locale.getAvailableLocales();
        List jdkLocaleList = Arrays.asList(jdkLocaleArray);
        Set jdkLocaleSet = new HashSet(jdkLocaleList);
        assertEquals(jdkLocaleSet, set);
    }