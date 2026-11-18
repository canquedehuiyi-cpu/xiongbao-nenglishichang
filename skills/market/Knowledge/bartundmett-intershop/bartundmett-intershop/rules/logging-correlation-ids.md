---
title: Use Correlation IDs for Distributed Tracing
impact: HIGH
impactDescription: enables tracing requests across services and components
tags: logging, tracing, correlation-id, observability, distributed
---

## Use Correlation IDs for Distributed Tracing

**Impact: HIGH (enables tracing requests across services and components)**

Every request should have a unique correlation ID that propagates through all services, enabling end-to-end tracing of distributed transactions.

**Incorrect (no correlation):**

```java
// Bad: Logs without correlation - impossible to trace
// Service A
logger.info("Received order request");
orderService.createOrder(request);

// Service B (downstream)
logger.info("Processing payment");
paymentGateway.process(payment);

// Service C (downstream)
logger.info("Sending confirmation email");
// Which order? Which payment? No way to correlate!
```

**Correct (correlation ID throughout):**

```java
// Good: Generate or extract correlation ID at entry point
@Provider
@Priority(Priorities.HEADER_DECORATOR)
public class CorrelationIdFilter implements ContainerRequestFilter {

    private static final String CORRELATION_ID_HEADER = "X-Correlation-ID";

    @Override
    public void filter(ContainerRequestContext request) {
        String correlationId = request.getHeaderString(CORRELATION_ID_HEADER);

        if (correlationId == null || correlationId.isEmpty()) {
            correlationId = generateCorrelationId();
        }

        // Store in MDC for automatic inclusion in logs
        MDC.put("correlationId", correlationId);

        // Store in request context for propagation
        request.setProperty("correlationId", correlationId);
    }

    private String generateCorrelationId() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }
}

// Good: Include correlation ID in response
@Provider
public class CorrelationIdResponseFilter implements ContainerResponseFilter {

    @Override
    public void filter(ContainerRequestContext request, ContainerResponseContext response) {
        String correlationId = MDC.get("correlationId");
        if (correlationId != null) {
            response.getHeaders().add("X-Correlation-ID", correlationId);
        }
    }
}

// Good: Propagate to downstream services
@Injectable
public class ExternalServiceClient {

    @Inject
    private WebTarget target;

    public PaymentResult processPayment(PaymentRequest payment) {
        String correlationId = MDC.get("correlationId");

        Response response = target.path("/payments")
            .request()
            .header("X-Correlation-ID", correlationId)  // Propagate!
            .post(Entity.json(payment));

        return response.readEntity(PaymentResult.class);
    }
}
```

**Correlation in async processing:**

```java
// Good: Preserve correlation ID in async tasks
public class CorrelationAwareExecutor {

    private final ExecutorService executor;

    public CorrelationAwareExecutor(ExecutorService executor) {
        this.executor = executor;
    }

    public <T> CompletableFuture<T> submit(Callable<T> task) {
        // Capture current correlation context
        String correlationId = MDC.get("correlationId");
        String userId = MDC.get("userId");

        return CompletableFuture.supplyAsync(() -> {
            try {
                // Restore context in async thread
                MDC.put("correlationId", correlationId);
                MDC.put("userId", userId);

                return task.call();
            } catch (Exception e) {
                throw new CompletionException(e);
            } finally {
                MDC.clear();
            }
        }, executor);
    }
}

// Usage
@Injectable
public class OrderService {

    @Inject
    private CorrelationAwareExecutor executor;

    public void processOrderAsync(Order order) {
        // Correlation ID automatically preserved
        executor.submit(() -> {
            logger.info("Processing order in background",
                kv("orderId", order.getId()));
            return processOrder(order);
        });
    }
}
```

**Correlation in event-driven systems:**

```java
// Good: Include correlation in events
public class OrderPlacedEvent {

    private String eventId;
    private String correlationId;  // Trace back to original request
    private String causationId;    // Which event caused this event
    private String orderId;
    private Instant timestamp;

    public OrderPlacedEvent(String orderId) {
        this.eventId = UUID.randomUUID().toString();
        this.correlationId = MDC.get("correlationId");
        this.causationId = MDC.get("currentEventId");
        this.orderId = orderId;
        this.timestamp = Instant.now();
    }
}

// Good: Event handler restores correlation context
public class OrderEventHandler {

    @EventListener
    public void handleOrderPlaced(OrderPlacedEvent event) {
        MDC.put("correlationId", event.getCorrelationId());
        MDC.put("causationId", event.getEventId());

        try {
            logger.info("Handling order placed event",
                kv("orderId", event.getOrderId()),
                kv("eventId", event.getEventId()));

            // Process event...

        } finally {
            MDC.clear();
        }
    }
}
```

**Correlation ID structure:**

| Field | Purpose | Example |
|-------|---------|---------|
| correlationId | Unique per user request | `a1b2c3d4e5f6` |
| requestId | Unique per service call | `req-12345` |
| spanId | Unique per operation | `span-001` |
| causationId | Parent event/operation | `evt-789` |

**Viewing correlated logs:**

```
# Find all logs for a single request
grep "correlationId=a1b2c3d4" /var/log/icm/*.log

# Or in log aggregator (Elasticsearch/Kibana)
correlationId: "a1b2c3d4e5f6"
```

Reference: [Distributed Tracing Best Practices](https://opentelemetry.io/docs/concepts/signals/traces/)
