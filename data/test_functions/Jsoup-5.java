    @Test public void parsesQuiteRoughAttributes() {
        String html = "<p =a>One<a =a";
        Document doc = Jsoup.parse(html);
        assertEquals("<p>One<a></a></p>", doc.body().html());
        
        doc = Jsoup.parse("<p .....");
        assertEquals("<p></p>", doc.body().html());
        
        doc = Jsoup.parse("<p .....<p!!");
        assertEquals("<p></p>\n<p></p>", doc.body().html());
    }