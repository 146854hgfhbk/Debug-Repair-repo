    public void testSerialization() {

        ShapeList l1 = new ShapeList();
        l1.setShape(0, new Rectangle(1, 2, 3, 4));
        l1.setShape(1, new Line2D.Double(1.0, 2.0, 3.0, 4.0));
        l1.setShape(2, null);

        ShapeList l2 = null;

        try {
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            ObjectOutput out = new ObjectOutputStream(buffer);
            out.writeObject(l1);
            out.close();

            ObjectInput in = new ObjectInputStream(new ByteArrayInputStream(
            		buffer.toByteArray()));
            l2 = (ShapeList) in.readObject();
            in.close();
        }
        catch (Exception e) {
            e.printStackTrace();
        }
        assertEquals(l1, l2);

    }