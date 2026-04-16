    public void testCodec98NPE() throws Exception {
        byte[] codec98 = StringUtils.getBytesUtf8(Base64TestData.CODEC_98_NPE);
        ByteArrayInputStream data = new ByteArrayInputStream(codec98);
        Base64InputStream stream = new Base64InputStream(data);

        // This line causes an NPE in commons-codec-1.4.jar:
        byte[] decodedBytes = Base64TestData.streamToBytes(stream, new byte[1024]);

        String decoded = StringUtils.newStringUtf8(decodedBytes);
        assertEquals(
            "codec-98 NPE Base64InputStream", Base64TestData.CODEC_98_NPE_DECODED, decoded
        );
    }