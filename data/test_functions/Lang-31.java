	public void testContainsAnyCharArrayWithSupplementaryChars() {
		assertEquals(true, StringUtils.containsAny(CharU20000 + CharU20001, CharU20000.toCharArray()));
		assertEquals(true, StringUtils.containsAny(CharU20000 + CharU20001, CharU20001.toCharArray()));
		assertEquals(true, StringUtils.containsAny(CharU20000, CharU20000.toCharArray()));
		// Sanity check:
		assertEquals(-1, CharU20000.indexOf(CharU20001));
		assertEquals(0, CharU20000.indexOf(CharU20001.charAt(0)));
		assertEquals(-1, CharU20000.indexOf(CharU20001.charAt(1)));
		// Test:
		assertEquals(false, StringUtils.containsAny(CharU20000, CharU20001.toCharArray()));
		assertEquals(false, StringUtils.containsAny(CharU20001, CharU20000.toCharArray()));
	}