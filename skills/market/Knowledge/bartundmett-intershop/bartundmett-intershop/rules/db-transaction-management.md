---
title: Use Proper Transaction Boundaries
impact: CRITICAL
impactDescription: ensures data consistency and prevents partial updates
tags: database, transactions, consistency, rollback
---

## Use Proper Transaction Boundaries

**Impact: CRITICAL (ensures data consistency and prevents partial updates)**

Transactions must wrap complete business operations to ensure atomicity. A transaction should either complete fully or roll back entirely.

**Incorrect (improper transaction boundaries):**

```java
// Bad: No transaction - partial updates possible
public void processOrder(OrderBO order) {
    // If payment succeeds but inventory update fails,
    // we have an inconsistent state!
    paymentService.chargeCustomer(order);
    inventoryService.reserveItems(order);
    orderRepository.updateStatus(order, OrderStatus.PROCESSED);
    notificationService.sendConfirmation(order);
}

// Bad: Transaction too broad - holds locks too long
@Transactional
public void processAllPendingOrders() {
    List<OrderBO> orders = orderRepository.getPendingOrders();
    for (OrderBO order : orders) {
        // Could be 1000s of orders in one transaction!
        processOrder(order);
    }
}

// Bad: Swallowing exceptions inside transaction
@Transactional
public void updateOrder(OrderBO order) {
    try {
        orderRepository.save(order);
        externalService.notify(order);  // If this fails...
    } catch (Exception e) {
        logger.error("External notification failed", e);
        // Transaction still commits with partial state!
    }
}
```

**Correct (proper transaction management):**

```java
// Good: Transaction wraps complete business operation
@Injectable
public class OrderProcessingService {

    @Inject
    private TransactionManager transactionManager;

    public void processOrder(OrderBO order) {
        // Transactional: charge, reserve, update status
        transactionManager.executeInTransaction(() -> {
            paymentService.chargeCustomer(order);
            inventoryService.reserveItems(order);
            orderRepository.updateStatus(order, OrderStatus.PROCESSED);
        });

        // Non-transactional: notification (can fail independently)
        try {
            notificationService.sendConfirmation(order);
        } catch (NotificationException e) {
            // Log and continue - order is already processed
            logger.warn("Failed to send notification", kv("orderId", order.getId()));
            notificationQueue.scheduleRetry(order);
        }
    }
}

// Good: Process items individually with separate transactions
public void processAllPendingOrders() {
    List<OrderBO> orders = orderRepository.getPendingOrders();

    for (OrderBO order : orders) {
        try {
            // Each order in its own transaction
            transactionManager.executeInTransaction(() -> {
                processOrder(order);
            });
        } catch (Exception e) {
            // One failure doesn't affect others
            logger.error("Failed to process order",
                kv("orderId", order.getId()), e);
            markOrderFailed(order, e);
        }
    }
}

// Good: Explicit rollback on business rule violation
@Transactional
public void transferFunds(Account from, Account to, Money amount) {
    from.debit(amount);

    if (from.getBalance().isNegative()) {
        // Explicit rollback
        throw new InsufficientFundsException(from, amount);
    }

    to.credit(amount);
    auditService.logTransfer(from, to, amount);
}
```

**Transaction propagation:**

```java
// Good: REQUIRED (default) - join existing or create new
@Transactional(propagation = Propagation.REQUIRED)
public void createOrder(OrderRequest request) {
    // Joins caller's transaction if exists
}

// Good: REQUIRES_NEW - always new transaction
@Transactional(propagation = Propagation.REQUIRES_NEW)
public void logAuditEvent(AuditEvent event) {
    // Audit must be saved even if parent transaction rolls back
    auditRepository.save(event);
}

// Good: NESTED - savepoint within parent transaction
@Transactional(propagation = Propagation.NESTED)
public void processLineItem(LineItem item) {
    // Can roll back to savepoint without affecting parent
}
```

**Read-only optimization:**

```java
// Good: Read-only for queries - allows optimizations
@Transactional(readOnly = true)
public List<OrderBO> getOrderHistory(String customerId) {
    return orderRepository.findByCustomer(customerId);
}

// Good: Avoid accidental writes in read-only context
@Transactional(readOnly = true)
public OrderSummary getOrderSummary(String orderId) {
    OrderBO order = orderRepository.getOrder(orderId);
    // order.setViewedAt(new Date());  // Would throw exception!
    return buildSummary(order);
}
```

**Transaction boundaries checklist:**

| Pattern | Use Case |
|---------|----------|
| Single operation per TX | Independent items processing |
| All-or-nothing | Order creation with payment |
| Read-only | Queries and reports |
| REQUIRES_NEW | Audit logging, metrics |
| Short transactions | Avoid holding locks |
| Explicit rollback | Business rule violations |

Reference: [Concept - Transaction Management](https://knowledge.intershop.com/kb/index.php/Display/278Z46)
