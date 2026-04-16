    public void testHashAndEquals() {
        String doc1 = "<div id=1><p class=one>One</p><p class=one>One</p><p class=one>Two</p><p class=two>One</p></div>" +
                "<div id=2><p class=one>One</p><p class=one>One</p><p class=one>Two</p><p class=two>One</p></div>";

        Document doc = Jsoup.parse(doc1);
        Elements els = doc.select("p");

        /*
        for (Element el : els) {
            System.out.println(el.hashCode() + " - " + el.outerHtml());
        }

        0 1534787905 - <p class="one">One</p>
        1 1534787905 - <p class="one">One</p>
        2 1539683239 - <p class="one">Two</p>
        3 1535455211 - <p class="two">One</p>
        4 1534787905 - <p class="one">One</p>
        5 1534787905 - <p class="one">One</p>
        6 1539683239 - <p class="one">Two</p>
        7 1535455211 - <p class="two">One</p>
        */
        assertEquals(8, els.size());
        Element e0 = els.get(0);
        Element e1 = els.get(1);
        Element e2 = els.get(2);
        Element e3 = els.get(3);
        Element e4 = els.get(4);
        Element e5 = els.get(5);
        Element e6 = els.get(6);
        Element e7 = els.get(7);

        assertEquals(e0, e1);
        assertEquals(e0, e4);
        assertEquals(e0, e5);
        assertFalse(e0.equals(e2));
        assertFalse(e0.equals(e3));
        assertFalse(e0.equals(e6));
        assertFalse(e0.equals(e7));

        assertEquals(e0.hashCode(), e1.hashCode());
        assertEquals(e0.hashCode(), e4.hashCode());
        assertEquals(e0.hashCode(), e5.hashCode());
        assertFalse(e0.hashCode() == (e2.hashCode()));
        assertFalse(e0.hashCode() == (e3).hashCode());
        assertFalse(e0.hashCode() == (e6).hashCode());
        assertFalse(e0.hashCode() == (e7).hashCode());
    }