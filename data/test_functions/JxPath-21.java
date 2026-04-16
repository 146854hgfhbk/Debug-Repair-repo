    public void testMapValueEquality() {
        assertXPathValue(context, "map/b != map/a", Boolean.TRUE);
        assertXPathValue(context, "map/a != map/b", Boolean.TRUE);
        assertXPathValue(context, "map/a != map/c", Boolean.FALSE);
        assertXPathValue(context, "map/a = map/b", Boolean.FALSE);
        assertXPathValue(context, "map/a = map/c", Boolean.TRUE);
        assertXPathValue(context, "not(map/a = map/b)", Boolean.TRUE);
        assertXPathValue(context, "not(map/a = map/c)", Boolean.FALSE);
    }