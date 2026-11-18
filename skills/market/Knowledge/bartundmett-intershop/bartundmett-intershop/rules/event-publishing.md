---
title: Publish Domain Events for Loose Coupling
impact: MEDIUM
impactDescription: enables extensibility and decoupled integrations
tags: events, domain-events, decoupling, integration
---

## Publish Domain Events for Loose Coupling

**Impact: MEDIUM (enables extensibility and decoupled integrations)**

Domain events decouple business operations from their side effects. Publish events for significant state changes to enable extensibility without modifying core logic.

**Incorrect (tightly coupled side effects):**

```java
// Bad: All side effects coupled in one place
public class OrderService {

    @Inject
    private EmailService emailService;
    @Inject
    private InventoryService inventoryService;
    @Inject
    private ERPIntegration erpIntegration;
    @Inject
    private AnalyticsService analyticsService;
    @Inject
    private LoyaltyService loyaltyService;

    public void submitOrder(OrderBO order) {
        // Core logic
        order.setStatus(OrderStatus.SUBMITTED);
        orderRepository.save(order);

        // All side effects tightly coupled - hard to extend!
        emailService.sendOrderConfirmation(order);
        inventoryService.reserveStock(order);
        erpIntegration.createSalesOrder(order);
        analyticsService.trackOrderSubmission(order);
        loyaltyService.awardPoints(order.getCustomer(), order.getTotal());

        // Need to add another integration? Modify this class again!
    }
}
```

**Correct (event-driven architecture):**

```java
// Good: Define domain events
public class OrderSubmittedEvent implements DomainEvent {

    private final String orderId;
    private final String customerId;
    private final Money orderTotal;
    private final List<OrderLineItemDTO> lineItems;
    private final Instant occurredAt;

    public OrderSubmittedEvent(OrderBO order) {
        this.orderId = order.getId();
        this.customerId = order.getCustomer().getId();
        this.orderTotal = order.getTotal();
        this.lineItems = order.getLineItems().stream()
            .map(OrderLineItemDTO::from)
            .collect(Collectors.toList());
        this.occurredAt = Instant.now();
    }
}

// Good: Service publishes events, doesn't handle side effects
public class OrderService {

    @Inject
    private EventPublisher eventPublisher;

    public void submitOrder(OrderBO order) {
        // Core business logic only
        order.setStatus(OrderStatus.SUBMITTED);
        orderRepository.save(order);

        // Publish event - handlers do the rest
        eventPublisher.publish(new OrderSubmittedEvent(order));
    }
}

// Good: Event handlers for each concern
@EventListener
public class OrderConfirmationEmailHandler {

    @Inject
    private EmailService emailService;

    @HandleEvent
    public void onOrderSubmitted(OrderSubmittedEvent event) {
        emailService.sendOrderConfirmation(event.getOrderId());
    }
}

@EventListener
public class InventoryReservationHandler {

    @Inject
    private InventoryService inventoryService;

    @HandleEvent
    @Async  // Run asynchronously
    public void onOrderSubmitted(OrderSubmittedEvent event) {
        inventoryService.reserveStock(event.getOrderId(), event.getLineItems());
    }
}

@EventListener
public class ERPSyncHandler {

    @Inject
    private ERPIntegration erpIntegration;

    @HandleEvent
    @Async
    @Retryable(maxAttempts = 3)  // Retry on failure
    public void onOrderSubmitted(OrderSubmittedEvent event) {
        erpIntegration.createSalesOrder(event.getOrderId());
    }
}

@EventListener
public class LoyaltyPointsHandler {

    @Inject
    private LoyaltyService loyaltyService;

    @HandleEvent
    public void onOrderSubmitted(OrderSubmittedEvent event) {
        loyaltyService.awardPoints(event.getCustomerId(), event.getOrderTotal());
    }
}
```

**Event publishing implementation:**

```java
// Good: Event publisher with async support
@Injectable
public class EventPublisherImpl implements EventPublisher {

    @Inject
    private List<EventListener> listeners;

    @Inject
    private AsyncExecutor asyncExecutor;

    @Override
    public void publish(DomainEvent event) {
        String correlationId = MDC.get("correlationId");

        for (EventListener listener : listeners) {
            if (shouldHandle(listener, event)) {
                if (isAsync(listener)) {
                    asyncExecutor.submit(() -> {
                        MDC.put("correlationId", correlationId);
                        try {
                            invokeHandler(listener, event);
                        } finally {
                            MDC.clear();
                        }
                    });
                } else {
                    invokeHandler(listener, event);
                }
            }
        }
    }

    private void invokeHandler(EventListener listener, DomainEvent event) {
        try {
            listener.handle(event);
        } catch (Exception e) {
            logger.error("Event handler failed",
                kv("handler", listener.getClass().getSimpleName()),
                kv("event", event.getClass().getSimpleName()),
                e);

            if (!isAsync(listener)) {
                throw e;  // Sync handlers should fail the transaction
            }
            // Async handlers log and continue
        }
    }
}
```

**Event patterns for common scenarios:**

```java
// Good: Different events for different business scenarios
public class OrderEvents {

    // Order lifecycle events
    public static class OrderCreatedEvent implements DomainEvent { }
    public static class OrderSubmittedEvent implements DomainEvent { }
    public static class OrderPaidEvent implements DomainEvent { }
    public static class OrderShippedEvent implements DomainEvent { }
    public static class OrderDeliveredEvent implements DomainEvent { }
    public static class OrderCancelledEvent implements DomainEvent { }

    // Enrichment events
    public static class OrderNoteAddedEvent implements DomainEvent { }
    public static class OrderAddressChangedEvent implements DomainEvent { }
}
```

**Event handling best practices:**

| Practice | Description |
|----------|-------------|
| Immutable events | Events should be immutable value objects |
| Include IDs | Pass IDs, not full objects |
| Async by default | Non-critical handlers should be async |
| Idempotent handlers | Same event twice = same result |
| Correlation IDs | Propagate for tracing |
| Error isolation | One handler failure shouldn't affect others |

Reference: [Domain-Driven Design Events](https://martinfowler.com/eaaDev/DomainEvent.html)
