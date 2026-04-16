    public void should_return_empty_iterable() throws Exception {
        assertFalse(((Iterable) values.returnValueFor(Iterable.class)).iterator().hasNext());
    }