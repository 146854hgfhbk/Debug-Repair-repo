      public void testSimple() throws Exception {
          final ObjectMapper mapper = new ObjectMapper();
          final String json = aposToQuotes("{'schemas': [{\n"
              + "  'name': 'FoodMart'\n"
              + "}]}\n");
          mapper.readValue(json, JsonRoot.class);
      }