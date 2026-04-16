    public void should_spy_inner_class() throws Exception {
    	 
     class WithMockAndSpy {
    		@Spy private InnerStrength strength;
    		@Mock private List<String> list;

            abstract class InnerStrength {
            	private final String name;

            	InnerStrength() {
            		// Make sure that @Mock fields are always injected before @Spy fields.
            		assertNotNull(list);
            		// Make sure constructor is indeed called.
            		this.name = "inner";
            	}
            	
            	abstract String strength();
            	
            	String fullStrength() {
            		return name + " " + strength();
            	}
            }
    	}
		WithMockAndSpy outer = new WithMockAndSpy();
        MockitoAnnotations.initMocks(outer);
        when(outer.strength.strength()).thenReturn("strength");
        assertEquals("inner strength", outer.strength.fullStrength());
    }