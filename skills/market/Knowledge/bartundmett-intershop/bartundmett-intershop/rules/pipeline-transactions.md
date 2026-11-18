---
title: Handle Pipeline Transactions Correctly
impact: MEDIUM
impactDescription: ensures data consistency in multi-step workflows
tags: pipeline, transactions, consistency, rollback
---

## Handle Pipeline Transactions Correctly

**Impact: MEDIUM (ensures data consistency in multi-step workflows)**

Pipelines often span multiple business operations that must be atomic. Understand transaction boundaries and implement proper error handling for consistent data states.

**Incorrect (broken transaction handling):**

```xml
<!-- Bad: No transaction demarcation -->
<pipeline name="CreateOrder">
    <pipelet class="ValidateCart"/>
    <pipelet class="CreateOrderFromCart"/>
    <pipelet class="ProcessPayment"/>
    <pipelet class="SendConfirmationEmail"/>
    <!-- If email fails, order and payment are already committed! -->
</pipeline>

<!-- Bad: Too large transaction scope -->
<pipeline name="ImportProducts" transaction="REQUIRED">
    <pipelet class="ReadCSVFile"/>          <!-- Long running -->
    <pipelet class="ParseProducts"/>         <!-- Memory intensive -->
    <pipelet class="ValidateProducts"/>      <!-- Validation -->
    <pipelet class="SaveProducts"/>          <!-- DB write -->
    <pipelet class="UpdateSearchIndex"/>     <!-- External system -->
    <!-- One failure rolls back everything! -->
</pipeline>
```

```java
// Bad: Manual commit in pipelet
public class SaveOrderPipelet extends AbstractPipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        OrderPO order = createOrder(dict);
        em.persist(order);
        em.getTransaction().commit();  // Don't manually manage transactions!

        return PIPELET_NEXT;
    }
}
```

**Correct (proper transaction management):**

```xml
<!-- Good: Explicit transaction boundaries -->
<pipeline name="CreateOrder">
    <!-- Validation outside transaction -->
    <pipelet class="ValidateCart"/>
    <pipelet class="ValidateInventory"/>

    <!-- Core order creation in transaction -->
    <transaction mode="REQUIRED">
        <pipelet class="ReserveInventory"/>
        <pipelet class="CreateOrderFromCart"/>
        <pipelet class="CalculateTotals"/>
    </transaction>

    <!-- Payment in separate transaction (can retry) -->
    <transaction mode="REQUIRES_NEW">
        <pipelet class="ProcessPayment">
            <return name="error" value="PaymentError"/>
        </pipelet>
    </transaction>

    <!-- Non-critical operations outside transaction -->
    <pipelet class="SendConfirmationEmail"/>
    <pipelet class="UpdateAnalytics"/>

    <return name="success" value="OrderComplete"/>
    <return name="error" value="PaymentError"/>
</pipeline>
```

```java
// Good: Transaction-aware pipelet implementation
@Injectable
public class CreateOrderPipelet extends AbstractPipelet {

    @Inject
    private OrderRepository orderRepository;

    @Inject
    private InventoryService inventoryService;

    @Override
    @Transactional(propagation = Propagation.MANDATORY)  // Requires existing tx
    public int execute(PipelineDictionary dict) {
        try {
            CartBO cart = dict.get("Cart");

            // Create order - participates in pipeline transaction
            OrderPO order = createOrderFromCart(cart);
            orderRepository.save(order);

            // Reserve inventory - same transaction
            for (OrderItemPO item : order.getItems()) {
                inventoryService.reserve(item.getSKU(), item.getQuantity());
            }

            dict.put("Order", order);
            return PIPELET_NEXT;

        } catch (InsufficientInventoryException e) {
            dict.put("ErrorMessage", e.getMessage());
            return PIPELET_ERROR;  // Transaction will be rolled back
        }
    }
}

// Good: Compensating actions for distributed operations
@Injectable
public class OrderCreationService {

    @Inject
    private OrderRepository orderRepository;

    @Inject
    private PaymentService paymentService;

    @Inject
    private InventoryService inventoryService;

    @Transactional
    public OrderBO createOrder(CartBO cart) {
        // Step 1: Create order (local DB)
        OrderPO order = orderRepository.createFromCart(cart);

        // Step 2: Reserve inventory (local DB)
        String reservationId = inventoryService.reserve(order);

        try {
            // Step 3: Process payment (external service)
            PaymentResult payment = paymentService.process(order);

            if (!payment.isSuccessful()) {
                // Compensate: Release inventory
                inventoryService.release(reservationId);
                throw new PaymentException(payment.getError());
            }

            order.setPaymentId(payment.getTransactionId());
            order.setStatus(OrderStatus.CONFIRMED);

            return orderMapper.toBO(order);

        } catch (PaymentException e) {
            // Compensate: Release inventory
            inventoryService.release(reservationId);
            throw e;  // Transaction rolls back order creation
        }
    }
}

// Good: Saga pattern for long-running processes
@Injectable
public class OrderSagaService {

    @Inject
    private SagaManager sagaManager;

    public void executeOrderSaga(OrderBO order) {
        Saga saga = sagaManager.create("order-creation-" + order.getId());

        saga.step("reserve-inventory")
            .action(() -> inventoryService.reserve(order))
            .compensation(() -> inventoryService.release(order));

        saga.step("process-payment")
            .action(() -> paymentService.charge(order))
            .compensation(() -> paymentService.refund(order));

        saga.step("create-shipment")
            .action(() -> shippingService.createShipment(order))
            .compensation(() -> shippingService.cancelShipment(order));

        saga.step("notify-warehouse")
            .action(() -> warehouseService.notify(order))
            .compensation(() -> warehouseService.cancel(order));

        try {
            saga.execute();
        } catch (SagaException e) {
            // Saga automatically executes compensations in reverse order
            logger.error("Order saga failed: {}", e.getMessage());
            throw new OrderCreationException("Order creation failed", e);
        }
    }
}

// Good: Idempotent operations for retry safety
@Injectable
public class IdempotentPaymentPipelet extends AbstractPipelet {

    @Inject
    private PaymentService paymentService;

    @Inject
    private IdempotencyKeyService idempotencyService;

    @Override
    public int execute(PipelineDictionary dict) {
        OrderBO order = dict.get("Order");
        String idempotencyKey = "payment-" + order.getId();

        // Check if already processed
        PaymentResult existing = idempotencyService.get(idempotencyKey);
        if (existing != null) {
            dict.put("PaymentResult", existing);
            return PIPELET_NEXT;
        }

        // Process payment
        PaymentResult result = paymentService.process(order);

        // Store result for idempotency
        idempotencyService.store(idempotencyKey, result);

        dict.put("PaymentResult", result);
        return result.isSuccessful() ? PIPELET_NEXT : PIPELET_ERROR;
    }
}
```

**Transaction modes:**

| Mode | Behavior |
|------|----------|
| REQUIRED | Join existing or create new |
| REQUIRES_NEW | Always create new, suspend existing |
| MANDATORY | Must have existing, error if not |
| NOT_SUPPORTED | Execute without transaction |
| NEVER | Error if transaction exists |

Reference: [ICM Pipeline Transactions](https://knowledge.intershop.com/kb/index.php/Display/2X3012)
