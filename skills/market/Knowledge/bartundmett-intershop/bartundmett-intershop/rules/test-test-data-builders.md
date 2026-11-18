---
title: Use Test Data Builders for Readable Tests
impact: MEDIUM
impactDescription: improves test readability and reduces duplication
tags: testing, test-data, builders, patterns
---

## Use Test Data Builders for Readable Tests

**Impact: MEDIUM (improves test readability and reduces duplication)**

Test data builders create domain objects with sensible defaults, allowing tests to specify only the relevant properties for each scenario.

**Incorrect (verbose, repetitive test setup):**

```java
// Bad: Verbose, hard to see what's being tested
@Test
public void testOrderTotal() {
    Order order = new Order();
    order.setOrderID("ORD-001");
    order.setCustomerID("CUST-001");
    order.setStatus(OrderStatus.OPEN);
    order.setCreatedDate(new Date());
    order.setCurrency("EUR");
    order.setShippingAddress(createAddress());
    order.setBillingAddress(createAddress());

    OrderLineItem item1 = new OrderLineItem();
    item1.setSKU("PROD-001");
    item1.setQuantity(2);
    item1.setUnitPrice(Money.of(50, "EUR"));
    item1.setTaxRate(0.19);

    OrderLineItem item2 = new OrderLineItem();
    item2.setSKU("PROD-002");
    item2.setQuantity(1);
    item2.setUnitPrice(Money.of(30, "EUR"));
    item2.setTaxRate(0.19);

    order.setLineItems(Arrays.asList(item1, item2));

    // Finally the actual test - 25 lines of setup!
    Money total = orderService.calculateTotal(order);
    assertEquals(Money.of(154.70, "EUR"), total);
}
```

**Correct (fluent builder with sensible defaults):**

```java
// Good: Clear, focused test setup
@Test
public void testOrderTotal_multipleItems_sumsWithTax() {
    Order order = anOrder()
        .withLineItem(aLineItem().withQuantity(2).withUnitPrice(50).build())
        .withLineItem(aLineItem().withQuantity(1).withUnitPrice(30).build())
        .build();

    Money total = orderService.calculateTotal(order);

    assertEquals(Money.of(154.70, "EUR"), total);  // (2*50 + 30) * 1.19
}

@Test
public void testOrderTotal_emptyOrder_returnsZero() {
    Order order = anOrder().withNoLineItems().build();

    Money total = orderService.calculateTotal(order);

    assertEquals(Money.ZERO_EUR, total);
}

@Test
public void testOrderTotal_withDiscount_appliesBeforeTax() {
    Order order = anOrder()
        .withLineItem(aLineItem().withUnitPrice(100).build())
        .withDiscount(Percentage.of(10))
        .build();

    Money total = orderService.calculateTotal(order);

    assertEquals(Money.of(107.10, "EUR"), total);  // (100 - 10%) * 1.19
}
```

**Builder implementation:**

```java
public class TestOrderBuilder {

    private String orderId = "ORD-" + UUID.randomUUID().toString().substring(0, 8);
    private String customerId = "CUST-DEFAULT";
    private OrderStatus status = OrderStatus.OPEN;
    private List<OrderLineItem> lineItems = new ArrayList<>();
    private Percentage discount = Percentage.ZERO;
    private String currency = "EUR";

    public static TestOrderBuilder anOrder() {
        return new TestOrderBuilder();
    }

    public TestOrderBuilder withOrderId(String orderId) {
        this.orderId = orderId;
        return this;
    }

    public TestOrderBuilder withCustomer(String customerId) {
        this.customerId = customerId;
        return this;
    }

    public TestOrderBuilder withStatus(OrderStatus status) {
        this.status = status;
        return this;
    }

    public TestOrderBuilder withLineItem(OrderLineItem item) {
        this.lineItems.add(item);
        return this;
    }

    public TestOrderBuilder withNoLineItems() {
        this.lineItems.clear();
        return this;
    }

    public TestOrderBuilder withDiscount(Percentage discount) {
        this.discount = discount;
        return this;
    }

    // Pre-configured scenarios
    public TestOrderBuilder asB2BOrder() {
        this.customerId = "B2B-CUST-001";
        return this;
    }

    public TestOrderBuilder asSubmitted() {
        this.status = OrderStatus.SUBMITTED;
        return this;
    }

    public Order build() {
        Order order = new Order();
        order.setOrderID(orderId);
        order.setCustomerID(customerId);
        order.setStatus(status);
        order.setLineItems(lineItems);
        order.setDiscount(discount);
        order.setCurrency(currency);
        order.setCreatedDate(new Date());
        return order;
    }
}

public class TestLineItemBuilder {

    private String sku = "PROD-DEFAULT";
    private int quantity = 1;
    private Money unitPrice = Money.of(10, "EUR");
    private BigDecimal taxRate = new BigDecimal("0.19");

    public static TestLineItemBuilder aLineItem() {
        return new TestLineItemBuilder();
    }

    public TestLineItemBuilder withSKU(String sku) {
        this.sku = sku;
        return this;
    }

    public TestLineItemBuilder withQuantity(int quantity) {
        this.quantity = quantity;
        return this;
    }

    public TestLineItemBuilder withUnitPrice(double price) {
        this.unitPrice = Money.of(price, "EUR");
        return this;
    }

    public OrderLineItem build() {
        OrderLineItem item = new OrderLineItem();
        item.setSKU(sku);
        item.setQuantity(quantity);
        item.setUnitPrice(unitPrice);
        item.setTaxRate(taxRate);
        return item;
    }
}
```

**Builder design principles:**

| Principle | Description |
|-----------|-------------|
| Sensible defaults | Valid object with minimal configuration |
| Fluent interface | Method chaining for readability |
| Scenario methods | `asB2BOrder()`, `asSubmitted()` for common cases |
| Static factory | `anOrder()` reads like English |
| Immutable result | Builder creates new object each time |

Reference: [Test Data Builders Pattern](https://www.natpryce.com/articles/000714.html)
