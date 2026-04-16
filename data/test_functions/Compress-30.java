    public void readOfLength0ShouldReturn0() throws Exception {
        // Create a big random piece of data
        byte[] rawData = new byte[1048576];
        for (int i=0; i < rawData.length; ++i) {
            rawData[i] = (byte) Math.floor(Math.random()*256);
        }

        // Compress it
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        BZip2CompressorOutputStream bzipOut = new BZip2CompressorOutputStream(baos);
        bzipOut.write(rawData);
        bzipOut.flush();
        bzipOut.close();
        baos.flush();
        baos.close();

        // Try to read it back in
        ByteArrayInputStream bais = new ByteArrayInputStream(baos.toByteArray());
        BZip2CompressorInputStream bzipIn = new BZip2CompressorInputStream(bais);
        byte[] buffer = new byte[1024];
        Assert.assertEquals(1024, bzipIn.read(buffer, 0, 1024));
        Assert.assertEquals(0, bzipIn.read(buffer, 1024, 0));
        Assert.assertEquals(1024, bzipIn.read(buffer, 0, 1024));
        bzipIn.close();
    }