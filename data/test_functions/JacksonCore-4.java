      public void testExpand()
      {
          TextBuffer tb = new TextBuffer(new BufferRecycler());
          char[] buf = tb.getCurrentSegment();

          while (buf.length < 500 * 1000) {
              char[] old = buf;
              buf = tb.expandCurrentSegment();
              if (old.length >= buf.length) {
                  fail("Expected buffer of "+old.length+" to expand, did not, length now "+buf.length);
              }
          }
      }