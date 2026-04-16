    public void testRenderWrappedTextWordCut()
    {
        int width = 7;
        int padding = 0;
        String text = "Thisisatest.";
        String expected = "Thisisa" + EOL + 
                          "test.";
        
        StringBuffer sb = new StringBuffer();
        new HelpFormatter().renderWrappedText(sb, width, padding, text);
        assertEquals("cut and wrap", expected, sb.toString());
    }