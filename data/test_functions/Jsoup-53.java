    @Test public void attributeWithBrackets() {
        String html = "<div data='End]'>One</div> <div data='[Another)]]'>Two</div>";
        Document doc = Jsoup.parse(html);
        assertEquals("One", doc.select("div[data='End]'").first().text());
        assertEquals("Two", doc.select("div[data='[Another)]]'").first().text());
    }