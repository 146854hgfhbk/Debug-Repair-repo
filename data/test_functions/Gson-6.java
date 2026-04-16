  public void testNullSafeBugDeserialize() throws Exception {
    Device device = gson.fromJson("{'id':'ec57803e2'}", Device.class);
    assertEquals("ec57803e2", device.id);
  }