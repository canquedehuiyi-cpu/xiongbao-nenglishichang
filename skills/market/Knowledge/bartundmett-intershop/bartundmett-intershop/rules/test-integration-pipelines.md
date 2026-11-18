---
title: Integration Test Pipelines with Pipeline Test Framework
impact: HIGH
impactDescription: validates pipeline flow and pipelet integration
tags: testing, integration-tests, pipelines, pipelets
---

## Integration Test Pipelines with Pipeline Test Framework

**Impact: HIGH (validates pipeline flow and pipelet integration)**

Pipelines should be tested using ICM's pipeline test framework to verify the complete flow including transitions, error handling, and pipelet interactions.

**Incorrect (testing only individual pipelets):**

```java
// Bad: Only tests pipelet in isolation - misses flow issues
public class OrderPipeletTest {

    @Test
    public void testValidateOrderPipelet() {
        ValidateOrderPipelet pipelet = new ValidateOrderPipelet();
        PipelineDictionary dict = new PipelineDictionaryImpl();
        dict.put("Order", createOrder());

        int result = pipelet.execute(dict);

        assertEquals(Pipelet.PIPELET_NEXT, result);
    }
}
```

**Correct (pipeline integration test):**

```java
// Good: Tests complete pipeline flow
public class OrderProcessPipelineTest extends AbstractPipelineTest {

    @Override
    protected void configurePipeline() {
        // Configure test environment
        setPipeline("process/OrderProcess");
        setStartNode("ProcessOrder");
    }

    @Test
    public void testProcessOrder_validOrder_completesSuccessfully() {
        // Arrange - set up pipeline input
        OrderBO order = createValidTestOrder();
        getInputDictionary().put("Order", order);
        getInputDictionary().put("Customer", createTestCustomer());

        // Act - execute pipeline
        PipelineResult result = executePipeline();

        // Assert - verify outcome
        assertTrue("Pipeline should succeed", result.isSuccess());
        assertEquals("EndNode_Success", result.getEndNode());

        // Verify output
        OrderBO processedOrder = result.getOutputDictionary().get("Order");
        assertEquals(OrderStatus.PROCESSED, processedOrder.getStatus());
    }

    @Test
    public void testProcessOrder_invalidOrder_transitionsToError() {
        // Arrange - invalid order
        OrderBO order = createInvalidTestOrder();
        getInputDictionary().put("Order", order);

        // Act
        PipelineResult result = executePipeline();

        // Assert - verify error flow
        assertFalse("Pipeline should fail", result.isSuccess());
        assertEquals("EndNode_Error", result.getEndNode());

        String errorCode = result.getOutputDictionary().get("ErrorCode");
        assertEquals("ORDER_VALIDATION_FAILED", errorCode);
    }

    @Test
    public void testProcessOrder_paymentFailure_transitionsToPaymentError() {
        // Arrange - order that will fail payment
        OrderBO order = createOrderWithFailingPayment();
        getInputDictionary().put("Order", order);

        // Mock payment service to fail
        mockService(PaymentService.class, paymentService -> {
            when(paymentService.processPayment(any())).thenReturn(PaymentResult.DECLINED);
        });

        // Act
        PipelineResult result = executePipeline();

        // Assert
        assertEquals("EndNode_PaymentError", result.getEndNode());
    }

    private OrderBO createValidTestOrder() {
        return TestOrderBuilder.anOrder()
            .withSKU("PROD-001")
            .withQuantity(2)
            .withValidPayment()
            .build();
    }
}
```

**Testing multiple paths:**

```java
@RunWith(Parameterized.class)
public class OrderValidationPathsTest extends AbstractPipelineTest {

    @Parameters(name = "{0}")
    public static Collection<Object[]> testCases() {
        return Arrays.asList(new Object[][] {
            { "Valid order", createValidOrder(), "EndNode_Success" },
            { "Empty cart", createEmptyOrder(), "EndNode_EmptyCart" },
            { "Invalid address", createOrderWithBadAddress(), "EndNode_AddressError" },
            { "Out of stock", createOrderWithUnavailableProduct(), "EndNode_StockError" }
        });
    }

    private final String scenario;
    private final OrderBO order;
    private final String expectedEndNode;

    public OrderValidationPathsTest(String scenario, OrderBO order, String expectedEndNode) {
        this.scenario = scenario;
        this.order = order;
        this.expectedEndNode = expectedEndNode;
    }

    @Test
    public void testOrderValidationPath() {
        getInputDictionary().put("Order", order);

        PipelineResult result = executePipeline();

        assertEquals(expectedEndNode, result.getEndNode());
    }
}
```

**Pipeline test best practices:**

| Practice | Description |
|----------|-------------|
| Test all paths | Cover success, error, and edge cases |
| Mock external services | Isolate pipeline from external dependencies |
| Verify transitions | Check that correct end nodes are reached |
| Check dictionary | Verify output dictionary contents |
| Use test builders | Create test data with builder pattern |

Reference: [Guide - Pipeline Testing](https://knowledge.intershop.com/kb/index.php/Display/24Y887)
