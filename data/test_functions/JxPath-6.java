    public void testIterateVariable() throws Exception {
        assertXPathValueIterator(context, "$d", list("a", "b"));
        assertXPathValue(context, "$d = 'a'", Boolean.TRUE);
        assertXPathValue(context, "$d = 'b'", Boolean.TRUE);
    }