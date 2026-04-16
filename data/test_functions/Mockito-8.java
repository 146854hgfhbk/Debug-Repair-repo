    public void typeVariable_of_self_type() {
        GenericMetadataSupport genericMetadata = inferFrom(GenericsSelfReference.class).resolveGenericReturnType(firstNamedMethod("self", GenericsSelfReference.class));

        assertThat(genericMetadata.rawType()).isEqualTo(GenericsSelfReference.class);
    }