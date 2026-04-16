    public void testDynamicRootName() throws IOException
    {
        String xml;

        ObjectWriter w = _xmlMapper.writer().withRootName("rudy");

        xml = w.writeValueAsString(new StringBean("foo"));
        assertEquals("<rudy><text>foo</text></rudy>", xml);

        xml = w.writeValueAsString(new StringBean(null));
        assertEquals("<rudy><text/></rudy>", xml);

        // and even with null will respect configured root name
        xml = w.writeValueAsString(null);
        assertEquals("<rudy/>", xml);
    }