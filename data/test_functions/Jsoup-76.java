  @Test public void preSkipsFirstNewline() {
        Document doc = Jsoup.parse("<pre>\n\nOne\nTwo\n</pre>");
        Element pre = doc.selectFirst("pre");
        assertEquals("One\nTwo", pre.text());
        assertEquals("\nOne\nTwo\n", pre.wholeText());
  }