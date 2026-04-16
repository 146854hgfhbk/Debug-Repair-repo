    @Test public void fallbackToUtfIfCantEncode() throws IOException {
        // that charset can't be encoded, so make sure we flip to utf

        String in = "<html><meta charset=\"ISO-2022-CN\"/>One</html>";
        Document doc = Jsoup.parse(new ByteArrayInputStream(in.getBytes()), null, "");

        assertEquals("UTF-8", doc.charset().name());
        assertEquals("One", doc.text());

        String html = doc.outerHtml();
        assertEquals("<html><head><meta charset=\"UTF-8\"></head><body>One</body></html>", TextUtil.stripNewlines(html));
    }