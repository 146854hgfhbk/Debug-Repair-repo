    public void testConstructor() {
    	MultiplePiePlot plot = new MultiplePiePlot();
    	assertNull(plot.getDataset());

    	// the following checks that the plot registers itself as a listener
    	// with the dataset passed to the constructor - see patch 1943021
    	DefaultCategoryDataset dataset = new DefaultCategoryDataset();
    	plot = new MultiplePiePlot(dataset);
    	assertTrue(dataset.hasListener(plot));
    }