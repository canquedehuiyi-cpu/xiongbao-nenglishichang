---
title: Integrate Application Performance Monitoring
impact: HIGH
impactDescription: enables proactive performance management and issue detection
tags: monitoring, apm, metrics, observability, tracing
---

## Integrate Application Performance Monitoring

**Impact: HIGH (enables proactive performance management and issue detection)**

Production ICM applications require comprehensive monitoring for performance, availability, and error tracking. Proper APM integration enables proactive issue detection and performance optimization.

**Incorrect (no monitoring):**

```java
// Bad: No metrics or tracing
public class OrderService {

    public OrderBO createOrder(CartBO cart) {
        // No timing, no metrics, no tracing
        OrderBO order = new OrderBO();
        order.setItems(convertItems(cart));
        order.setTotal(calculateTotal(cart));
        orderRepository.save(order);
        return order;
    }

    public void processPayment(OrderBO order) {
        // No visibility into external service calls
        paymentGateway.charge(order.getTotal());
    }
}

// Bad: Swallowing errors without alerting
public void syncInventory() {
    try {
        inventoryService.sync();
    } catch (Exception e) {
        // Logged but no alerting!
        logger.error("Sync failed", e);
    }
}
```

**Correct (comprehensive monitoring):**

```java
// Good: Metrics instrumentation
@Injectable
public class OrderService {

    @Inject
    private MeterRegistry meterRegistry;

    @Inject
    private Tracer tracer;

    private final Counter orderCounter;
    private final Timer orderCreationTimer;
    private final DistributionSummary orderValueSummary;

    @Inject
    public OrderService(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;

        // Counter for order volume
        this.orderCounter = Counter.builder("orders.created")
            .description("Total orders created")
            .tag("service", "order")
            .register(meterRegistry);

        // Timer for order creation latency
        this.orderCreationTimer = Timer.builder("orders.creation.time")
            .description("Order creation latency")
            .publishPercentiles(0.5, 0.95, 0.99)
            .register(meterRegistry);

        // Distribution of order values
        this.orderValueSummary = DistributionSummary.builder("orders.value")
            .description("Order value distribution")
            .baseUnit("currency")
            .register(meterRegistry);
    }

    public OrderBO createOrder(CartBO cart) {
        // Create span for distributed tracing
        Span span = tracer.spanBuilder("createOrder")
            .setAttribute("cart.id", cart.getId())
            .setAttribute("cart.items", cart.getItemCount())
            .startSpan();

        try (Scope scope = span.makeCurrent()) {
            return orderCreationTimer.record(() -> {
                OrderBO order = doCreateOrder(cart);

                // Record metrics
                orderCounter.increment();
                orderValueSummary.record(order.getTotal().doubleValue());

                // Add order info to span
                span.setAttribute("order.id", order.getId());
                span.setAttribute("order.total", order.getTotal().doubleValue());

                return order;
            });

        } catch (Exception e) {
            span.setStatus(StatusCode.ERROR, e.getMessage());
            span.recordException(e);
            throw e;

        } finally {
            span.end();
        }
    }
}

// Good: External service monitoring
@Injectable
public class PaymentGatewayClient {

    @Inject
    private MeterRegistry meterRegistry;

    @Inject
    private Tracer tracer;

    @Inject
    private CircuitBreakerRegistry circuitBreakerRegistry;

    private final Timer paymentTimer;
    private final Counter paymentSuccessCounter;
    private final Counter paymentFailureCounter;

    public PaymentResult charge(OrderBO order) {
        Span span = tracer.spanBuilder("paymentGateway.charge")
            .setSpanKind(SpanKind.CLIENT)
            .setAttribute("payment.amount", order.getTotal().doubleValue())
            .setAttribute("payment.currency", order.getCurrency().getCode())
            .startSpan();

        Timer.Sample sample = Timer.start(meterRegistry);

        try (Scope scope = span.makeCurrent()) {
            PaymentResult result = circuitBreaker.executeSupplier(() ->
                paymentGateway.charge(order)
            );

            if (result.isSuccessful()) {
                paymentSuccessCounter.increment();
                span.setAttribute("payment.transaction_id", result.getTransactionId());
            } else {
                paymentFailureCounter.increment();
                span.setAttribute("payment.error", result.getErrorCode());
            }

            return result;

        } catch (Exception e) {
            paymentFailureCounter.increment();
            span.setStatus(StatusCode.ERROR, e.getMessage());
            span.recordException(e);
            throw e;

        } finally {
            sample.stop(paymentTimer);
            span.end();
        }
    }
}

// Good: Health check endpoints
@RestController
@RequestMapping("/health")
public class HealthController {

    @Inject
    private List<HealthIndicator> healthIndicators;

    @GetMapping("/live")
    public ResponseEntity<Map<String, String>> liveness() {
        // Basic liveness - is the app running?
        return ResponseEntity.ok(Map.of("status", "UP"));
    }

    @GetMapping("/ready")
    public ResponseEntity<HealthStatus> readiness() {
        // Readiness - can the app serve traffic?
        Map<String, HealthStatus> components = new LinkedHashMap<>();
        boolean allHealthy = true;

        for (HealthIndicator indicator : healthIndicators) {
            HealthStatus status = indicator.health();
            components.put(indicator.getName(), status);
            if (!status.isUp()) {
                allHealthy = false;
            }
        }

        HealthStatus overall = new HealthStatus(
            allHealthy ? "UP" : "DOWN",
            components
        );

        return ResponseEntity
            .status(allHealthy ? 200 : 503)
            .body(overall);
    }
}

// Good: Database health indicator
@Injectable
public class DatabaseHealthIndicator implements HealthIndicator {

    @Inject
    private DataSource dataSource;

    @Override
    public String getName() {
        return "database";
    }

    @Override
    public HealthStatus health() {
        try (Connection conn = dataSource.getConnection()) {
            try (Statement stmt = conn.createStatement()) {
                stmt.execute("SELECT 1");
            }
            return HealthStatus.up()
                .withDetail("type", "Oracle")
                .withDetail("pool.active", getActiveConnections())
                .build();

        } catch (SQLException e) {
            return HealthStatus.down()
                .withDetail("error", e.getMessage())
                .build();
        }
    }
}

// Good: Custom business metrics
@Injectable
public class BusinessMetricsService {

    @Inject
    private MeterRegistry meterRegistry;

    @Scheduled(fixedRate = 60000)  // Every minute
    public void recordBusinessMetrics() {
        // Active shopping carts
        meterRegistry.gauge("business.carts.active",
            cartRepository.countActiveCarts());

        // Pending orders
        meterRegistry.gauge("business.orders.pending",
            orderRepository.countByStatus(OrderStatus.PENDING));

        // Low stock items
        meterRegistry.gauge("business.inventory.low_stock",
            inventoryRepository.countLowStockItems());

        // Failed payments in last hour
        meterRegistry.gauge("business.payments.failed.hourly",
            paymentRepository.countFailedLastHour());
    }
}

// Good: Alert-worthy error handling
@Injectable
public class AlertingErrorHandler {

    @Inject
    private MeterRegistry meterRegistry;

    @Inject
    private AlertService alertService;

    public void handleCriticalError(String operation, Exception e) {
        // Increment error counter for alerting
        Counter.builder("errors.critical")
            .tag("operation", operation)
            .tag("exception", e.getClass().getSimpleName())
            .register(meterRegistry)
            .increment();

        // Log with correlation
        logger.error("Critical error in {}: {}", operation, e.getMessage(), e);

        // Send immediate alert for critical operations
        if (isCriticalOperation(operation)) {
            alertService.sendAlert(
                AlertLevel.CRITICAL,
                String.format("Critical failure in %s", operation),
                e
            );
        }
    }
}
```

**Prometheus metrics configuration:**

```yaml
# application.yml
management:
  endpoints:
    web:
      exposure:
        include: health,metrics,prometheus
  metrics:
    tags:
      application: icm-storefront
      environment: ${ENVIRONMENT:development}
    export:
      prometheus:
        enabled: true
```

**Key metrics to monitor:**

| Category | Metrics |
|----------|---------|
| Request | Latency (p50, p95, p99), throughput, error rate |
| JVM | Heap usage, GC pauses, thread count |
| Database | Connection pool, query time, active connections |
| Cache | Hit rate, evictions, size |
| Business | Order volume, cart conversion, failed payments |
| External | API latency, circuit breaker state, retry count |

Reference: [ICM Monitoring Guide](https://knowledge.intershop.com/kb/index.php/Display/2X3102)
