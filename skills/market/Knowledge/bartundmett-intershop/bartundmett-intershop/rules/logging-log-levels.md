---
title: Use Appropriate Log Levels
impact: MEDIUM
impactDescription: balances observability with log volume and noise
tags: logging, log-levels, observability, debugging
---

## Use Appropriate Log Levels

**Impact: MEDIUM (balances observability with log volume and noise)**

Use the correct log level for each message type. Too many INFO logs creates noise; too few means missing crucial debugging information.

**Incorrect (improper log levels):**

```java
// Bad: Everything at INFO - too noisy
public void processOrder(Order order) {
    logger.info("Entering processOrder");
    logger.info("Validating order");
    logger.info("Order validation passed");
    logger.info("Calculating totals");
    logger.info("Total calculated: " + total);
    logger.info("Saving order");
    logger.info("Order saved");
    logger.info("Exiting processOrder");
}

// Bad: Important events at DEBUG - invisible in production
public void paymentDeclined(Payment payment) {
    logger.debug("Payment was declined");  // Should be WARN!
}

// Bad: ERROR for non-errors
public User findUser(String id) {
    User user = userRepository.findById(id);
    if (user == null) {
        logger.error("User not found");  // Not an error, expected case!
    }
    return user;
}

// Bad: Missing stack trace
try {
    riskyOperation();
} catch (Exception e) {
    logger.error("Operation failed: " + e.getMessage());  // Stack trace lost!
}
```

**Correct (appropriate log levels):**

```java
public class OrderService {

    private static final Logger logger = LoggerFactory.getLogger(OrderService.class);

    public OrderBO processOrder(OrderRequest request) {

        // TRACE: Method entry/exit, loop iterations, very detailed
        // Only enable for deep debugging specific issues
        logger.trace("Entering processOrder", kv("requestId", request.getId()));

        // DEBUG: Detailed info useful for debugging
        // Enable in development/staging, usually off in production
        logger.debug("Validating order request",
            kv("itemCount", request.getItems().size()),
            kv("totalValue", request.getTotal()));

        OrderBO order = validateAndCreate(request);

        // INFO: Business events, state changes, key operations
        // Always enabled - should be meaningful, not verbose
        logger.info("Order created",
            kv("orderId", order.getId()),
            kv("status", order.getStatus()),
            kv("total", order.getTotal()));

        return order;
    }

    public void processPayment(OrderBO order) {
        PaymentResult result = paymentService.process(order);

        if (result.isSuccess()) {
            // INFO: Successful business operation
            logger.info("Payment successful",
                kv("orderId", order.getId()),
                kv("transactionId", result.getTransactionId()));

        } else if (result.isDeclined()) {
            // WARN: Business exception, recoverable, but unusual
            logger.warn("Payment declined",
                kv("orderId", order.getId()),
                kv("reason", result.getDeclineReason()),
                kv("retryable", result.isRetryable()));

        } else {
            // ERROR: Technical failure requiring attention
            logger.error("Payment processing error",
                kv("orderId", order.getId()),
                kv("errorCode", result.getErrorCode()),
                result.getException());  // Include stack trace!
        }
    }

    public UserBO findUser(String userId) {
        UserBO user = userRepository.findById(userId);

        if (user == null) {
            // DEBUG: Expected case, not an error
            logger.debug("User not found", kv("userId", userId));
        }

        return user;  // Caller handles null appropriately
    }
}
```

**Log level decision guide:**

| Level | Use For | Production | Example |
|-------|---------|------------|---------|
| TRACE | Very detailed debugging | OFF | Loop iterations, method entry/exit |
| DEBUG | Development debugging | Usually OFF | Variable values, decision points |
| INFO | Business events | ON | Order created, payment processed |
| WARN | Unusual situations | ON | Payment declined, retry attempted |
| ERROR | Failures needing action | ON | Service unavailable, data corruption |

**Common patterns:**

```java
// Good: Exception handling with proper levels
try {
    externalService.call();
} catch (TimeoutException e) {
    // WARN: Transient, will retry
    logger.warn("External service timeout, retrying",
        kv("attempt", attempt),
        kv("maxAttempts", maxAttempts));
} catch (ServiceUnavailableException e) {
    // ERROR: Service down, needs attention
    logger.error("External service unavailable",
        kv("service", "payment-gateway"),
        e);
}

// Good: Conditional debug logging (avoids string building when disabled)
if (logger.isDebugEnabled()) {
    logger.debug("Processing items",
        kv("items", items.stream()
            .map(Item::getId)
            .collect(Collectors.toList())));
}

// Good: Performance-sensitive code
logger.atDebug()
    .addKeyValue("largeObject", () -> expensiveToString(obj))  // Lazy evaluation
    .log("Processing complete");
```

**Log volume guidelines:**

| Level | Target Rate | If Exceeded |
|-------|-------------|-------------|
| ERROR | < 1/minute | Investigate immediately |
| WARN | < 10/minute | Review weekly |
| INFO | < 100/second | Reduce verbosity |
| DEBUG | Disabled in prod | Enable temporarily |

Reference: [SLF4J Documentation](https://www.slf4j.org/manual.html)
