    public void littleEndianWithOverflow() throws Exception {
        ByteArrayInputStream in = new ByteArrayInputStream(new byte[] {
                87, // 01010111
                45, // 00101101
                66, // 01000010
                15, // 00001111
                90, // 01011010
                29, // 00011101
                88, // 01011000
                61, // 00111101
                33, // 00100001
                74  // 01001010
            });
        BitInputStream bin = new BitInputStream(in, ByteOrder.LITTLE_ENDIAN);
        assertEquals(23, // 10111
                     bin.readBits(5));
        assertEquals(714595605644185962l, // 0001-00111101-01011000-00011101-01011010-00001111-01000010-00101101-010
                     bin.readBits(63));
        assertEquals(1186, // 01001010-0010
                     bin.readBits(12));
        assertEquals(-1 , bin.readBits(1));
    }