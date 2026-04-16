    public void skipUsingRead() throws Exception {
        skip(new StreamWrapper() {
                public InputStream wrap(InputStream toWrap) {
                    return new FilterInputStream(toWrap) {
                        public long skip(long s) {
                            return 0;
                        }
                    };
                }
            });
    }