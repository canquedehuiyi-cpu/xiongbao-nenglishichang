---
title: Use Asynchronous Processing for Non-Critical Operations
impact: HIGH
impactDescription: reduces response times by 30-70% for complex workflows
tags: performance, async, parallel, non-blocking
---

## Use Asynchronous Processing for Non-Critical Operations

**Impact: HIGH (reduces response times by 30-70% for complex workflows)**

Operations that don't affect the immediate response should be processed asynchronously. This includes logging, analytics, notifications, and external system updates.

**Incorrect (synchronous blocking operations):**

```java
// Bad: All operations block the response
public class OrderPlacementPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        Order order = dict.get("Order");

        // Core operation - must be synchronous
        orderRepository.save(order);

        // These block the response but don't need to!
        emailService.sendOrderConfirmation(order);      // 200ms
        analyticsService.trackOrderPlaced(order);       // 100ms
        erpService.notifyNewOrder(order);               // 500ms
        inventoryService.reserveStock(order);           // 300ms
        auditService.logOrderCreation(order);           // 50ms

        // Total: 1150ms of unnecessary blocking!
        return PIPELET_NEXT;
    }
}
```

**Correct (non-blocking async operations):**

```java
// Good: Non-critical operations run asynchronously
public class OrderPlacementPipelet extends Pipelet {

    @Inject
    private AsyncExecutor asyncExecutor;

    @Inject
    private EventPublisher eventPublisher;

    @Override
    public int execute(PipelineDictionary dict) {
        Order order = dict.get("Order");

        // Core operation - synchronous
        orderRepository.save(order);

        // Publish event for async handlers
        eventPublisher.publish(new OrderPlacedEvent(order.getOrderID()));

        // Or use direct async execution
        asyncExecutor.submit(() -> emailService.sendOrderConfirmation(order));
        asyncExecutor.submit(() -> analyticsService.trackOrderPlaced(order));

        // Response returns immediately
        return PIPELET_NEXT;
    }
}

// Event-based async handlers
@Component
public class OrderPlacedEventHandler {

    @EventListener
    @Async
    public void handleOrderPlaced(OrderPlacedEvent event) {
        Order order = orderRepository.getOrder(event.getOrderId());

        // All non-critical processing happens here
        erpService.notifyNewOrder(order);
        inventoryService.reserveStock(order);
        auditService.logOrderCreation(order);
    }
}
```

**Using ICM's after() pattern (Next.js inspired):**

```java
// For ICM 12+: Use deferred execution
public class OrderPipelet extends Pipelet {

    @Inject
    private DeferredExecutor deferredExecutor;

    @Override
    public int execute(PipelineDictionary dict) {
        Order order = dict.get("Order");

        orderRepository.save(order);

        // Schedule for after response is sent
        deferredExecutor.after(() -> {
            // These run after the response, not blocking it
            sendNotifications(order);
            updateExternalSystems(order);
            logAnalytics(order);
        });

        return PIPELET_NEXT;
    }
}
```

**When to use async vs sync:**

| Operation Type | Approach | Reason |
|----------------|----------|--------|
| Order creation | Sync | Must complete before response |
| Payment processing | Sync | User needs immediate feedback |
| Email notifications | Async | Can tolerate delay |
| Analytics/logging | Async | Not user-visible |
| ERP sync | Async | External system, may be slow |
| Stock reservation | Depends | Critical = sync, soft = async |

Reference: [Concept - Technical Architecture of ICM 11+](https://knowledge.intershop.com/kb/index.php/Display/30983L)
