---
title: Use Structured Logging for Observability
impact: HIGH
impactDescription: enables efficient log searching and alerting
tags: logging, observability, monitoring, structured-logs
---

## Use Structured Logging for Observability

**Impact: HIGH (enables efficient log searching and alerting)**

Use structured logging with key-value pairs instead of string concatenation. This enables log aggregation tools to parse, search, and alert on specific fields.

**Incorrect (unstructured logging):**

```java
// Bad: String concatenation - hard to parse
logger.info("Order " + orderId + " created by user " + userId + " with total " + total);

// Bad: Inconsistent format
logger.info("Processing order: " + orderId);
logger.info("User [" + userId + "] placed order");
logger.info("Order total=" + total + " currency=" + currency);

// Bad: Missing context
logger.error("Failed to process payment");  // Which payment? Which order?

// Bad: Exception swallowing
try {
    processPayment(order);
} catch (Exception e) {
    logger.error("Payment failed: " + e.getMessage());  // Lost stack trace!
}
```

**Correct (structured logging with SLF4J):**

```java
// Good: Parameterized logging with key-value pairs
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import static net.logstash.logback.argument.StructuredArguments.*;

public class OrderService {

    private static final Logger logger = LoggerFactory.getLogger(OrderService.class);

    public OrderBO createOrder(OrderRequest request, UserBO user) {
        // Good: Structured log entry with searchable fields
        logger.info("Creating order",
            kv("orderId", request.getOrderId()),
            kv("userId", user.getId()),
            kv("customerType", user.getCustomerType()),
            kv("itemCount", request.getItems().size()),
            kv("total", request.getTotal()),
            kv("currency", request.getCurrency()));

        try {
            OrderBO order = orderRepository.create(request);

            // Good: Business event logging
            logger.info("Order created successfully",
                kv("orderId", order.getOrderId()),
                kv("status", order.getStatus()),
                kv("processingTimeMs", order.getProcessingTime()));

            return order;

        } catch (Exception e) {
            // Good: Error with full context and stack trace
            logger.error("Failed to create order",
                kv("orderId", request.getOrderId()),
                kv("userId", user.getId()),
                kv("errorType", e.getClass().getSimpleName()),
                e);  // Stack trace preserved

            throw e;
        }
    }
}
```

**MDC for request-scoped context:**

```java
// Good: Set MDC at request start
public class RequestContextFilter implements ContainerRequestFilter {

    @Override
    public void filter(ContainerRequestContext request) {
        // Add context available in all logs for this request
        MDC.put("requestId", generateRequestId());
        MDC.put("sessionId", extractSessionId(request));
        MDC.put("userId", extractUserId(request));
        MDC.put("clientIp", extractClientIp(request));
    }
}

// Good: Clear MDC at request end
public class RequestContextCleanupFilter implements ContainerResponseFilter {

    @Override
    public void filter(ContainerRequestContext request, ContainerResponseContext response) {
        MDC.clear();
    }
}

// Now all logs automatically include requestId, sessionId, etc.
logger.info("Processing payment", kv("amount", amount));
// Output: {"message":"Processing payment","amount":99.99,"requestId":"abc123","userId":"user456"}
```

**Log level guidelines:**

```java
// Good: Appropriate log levels
public class PaymentService {

    public PaymentResult processPayment(PaymentRequest request) {

        // TRACE: Very detailed, usually disabled
        logger.trace("Entering processPayment", kv("request", request));

        // DEBUG: Detailed info for debugging
        logger.debug("Validating payment request",
            kv("paymentMethod", request.getMethod()),
            kv("amount", request.getAmount()));

        // INFO: Business events, state changes
        logger.info("Processing payment",
            kv("orderId", request.getOrderId()),
            kv("amount", request.getAmount()));

        if (result.isDeclined()) {
            // WARN: Unusual but handled situations
            logger.warn("Payment declined",
                kv("orderId", request.getOrderId()),
                kv("reason", result.getDeclineReason()));
        }

        if (result.isError()) {
            // ERROR: Failures requiring attention
            logger.error("Payment processing error",
                kv("orderId", request.getOrderId()),
                kv("errorCode", result.getErrorCode()),
                result.getException());
        }

        return result;
    }
}
```

**Logback configuration for JSON output:**

```xml
<!-- logback.xml -->
<appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
        <includeMdcKeyNames>requestId,sessionId,userId</includeMdcKeyNames>
    </encoder>
</appender>
```

**Log structure standard:**

| Field | Type | Purpose |
|-------|------|---------|
| timestamp | ISO8601 | When event occurred |
| level | string | INFO, WARN, ERROR |
| logger | string | Class name |
| message | string | Human-readable description |
| requestId | string | Request correlation |
| userId | string | User context |
| orderId, etc. | varies | Business context |

Reference: [SLF4J Documentation](https://www.slf4j.org/manual.html)
