---
title: Consume Events Reliably
impact: MEDIUM
impactDescription: ensures reliable event-driven processing
tags: events, messaging, consumer, reliability
---

## Consume Events Reliably

**Impact: MEDIUM (ensures reliable event-driven processing)**

Event consumers must handle messages reliably with proper error handling, idempotency, and ordering guarantees where required.

**Incorrect (unreliable event consumption):**

```java
// Bad: No error handling
@EventListener
public void handleOrderCreated(OrderCreatedEvent event) {
    sendEmailNotification(event.getOrderId());  // Could fail!
}

// Bad: Not idempotent
@EventListener
public void handlePaymentReceived(PaymentReceivedEvent event) {
    inventoryService.ship(event.getOrderId());  // Ships again on redelivery!
}

// Bad: Blocking processing
@EventListener
public void handlePriceUpdated(PriceUpdatedEvent event) {
    updateAllProductListings(event);  // Long-running, blocks event queue
}

// Bad: No acknowledgment handling
public void processMessage(Message message) {
    try {
        process(message);
    } catch (Exception e) {
        // Message lost!
    }
}
```

**Correct (reliable event consumption):**

```java
// Good: Robust event consumer with error handling
@Injectable
public class OrderEventConsumer {

    @Inject
    private OrderService orderService;

    @Inject
    private RetryService retryService;

    @Inject
    private DeadLetterService deadLetterService;

    @EventListener
    @Transactional
    public void handleOrderCreated(OrderCreatedEvent event) {
        try {
            // Validate event
            if (event.getOrderId() == null) {
                logger.warn("Received invalid OrderCreatedEvent: missing orderId");
                return;
            }

            // Process
            processOrder(event);

        } catch (RetryableException e) {
            // Schedule retry
            retryService.scheduleRetry(event, e);

        } catch (Exception e) {
            // Move to dead letter queue
            deadLetterService.enqueue(event, e);
            logger.error("Failed to process OrderCreatedEvent", e);
        }
    }
}

// Good: Idempotent event processing
@Injectable
public class IdempotentEventConsumer {

    @Inject
    private ProcessedEventRepository processedEvents;

    @EventListener
    @Transactional
    public void handlePaymentReceived(PaymentReceivedEvent event) {
        String eventId = event.getEventId();

        // Check if already processed
        if (processedEvents.exists(eventId)) {
            logger.debug("Event {} already processed, skipping", eventId);
            return;
        }

        try {
            // Process event
            processPayment(event);

            // Record as processed
            processedEvents.save(new ProcessedEvent(
                eventId,
                event.getClass().getName(),
                Instant.now()
            ));

        } catch (Exception e) {
            // Don't mark as processed if failed
            throw e;
        }
    }
}

// Good: Async event processing with backpressure
@Injectable
public class AsyncEventProcessor {

    private final ExecutorService executor =
        new ThreadPoolExecutor(
            5,                               // Core pool size
            20,                              // Max pool size
            60, TimeUnit.SECONDS,
            new LinkedBlockingQueue<>(1000), // Bounded queue for backpressure
            new ThreadPoolExecutor.CallerRunsPolicy()  // Slow down producer
        );

    @Inject
    private EventProcessingService processingService;

    @EventListener
    public void handleBulkEvent(BulkDataEvent event) {
        // Submit for async processing
        CompletableFuture.runAsync(() -> {
            MDC.put("eventId", event.getEventId());
            try {
                processingService.process(event);
            } finally {
                MDC.clear();
            }
        }, executor).exceptionally(e -> {
            logger.error("Async event processing failed", e);
            return null;
        });
    }
}

// Good: Ordered event processing
@Injectable
public class OrderedEventConsumer {

    private final Map<String, Queue<DomainEvent>> entityQueues =
        new ConcurrentHashMap<>();

    private final Map<String, AtomicBoolean> processingFlags =
        new ConcurrentHashMap<>();

    @EventListener
    public void handleEvent(DomainEvent event) {
        String entityId = event.getEntityId();

        // Queue event for entity
        entityQueues
            .computeIfAbsent(entityId, k -> new ConcurrentLinkedQueue<>())
            .offer(event);

        // Process queue if not already processing
        processQueue(entityId);
    }

    private void processQueue(String entityId) {
        AtomicBoolean processing = processingFlags
            .computeIfAbsent(entityId, k -> new AtomicBoolean(false));

        if (!processing.compareAndSet(false, true)) {
            return;  // Already processing this entity's events
        }

        try {
            Queue<DomainEvent> queue = entityQueues.get(entityId);
            DomainEvent event;

            while ((event = queue.poll()) != null) {
                processEvent(event);
            }

        } finally {
            processing.set(false);

            // Check if more events arrived during processing
            Queue<DomainEvent> queue = entityQueues.get(entityId);
            if (queue != null && !queue.isEmpty()) {
                processQueue(entityId);
            }
        }
    }
}

// Good: Batch event consumer
@Injectable
public class BatchEventConsumer {

    private final List<InventoryUpdateEvent> buffer = new ArrayList<>();
    private final int BATCH_SIZE = 100;
    private final Duration BATCH_TIMEOUT = Duration.ofSeconds(5);
    private Instant lastFlush = Instant.now();

    @EventListener
    public synchronized void handleInventoryUpdate(InventoryUpdateEvent event) {
        buffer.add(event);

        if (shouldFlush()) {
            flushBuffer();
        }
    }

    private boolean shouldFlush() {
        return buffer.size() >= BATCH_SIZE ||
               Duration.between(lastFlush, Instant.now()).compareTo(BATCH_TIMEOUT) > 0;
    }

    @Transactional
    private void flushBuffer() {
        if (buffer.isEmpty()) {
            return;
        }

        try {
            // Batch process
            List<InventoryUpdateEvent> batch = new ArrayList<>(buffer);
            buffer.clear();

            inventoryService.updateBatch(batch);

        } finally {
            lastFlush = Instant.now();
        }
    }

    @Scheduled(fixedDelay = 5000)
    public synchronized void scheduledFlush() {
        flushBuffer();
    }
}

// Good: Event consumer with circuit breaker
@Injectable
public class CircuitBreakerEventConsumer {

    private final CircuitBreaker circuitBreaker = CircuitBreaker.builder()
        .failureRateThreshold(50)
        .waitDurationInOpenState(Duration.ofMinutes(1))
        .slidingWindowSize(10)
        .build();

    @EventListener
    public void handleExternalEvent(ExternalSystemEvent event) {
        Try.ofSupplier(
            CircuitBreaker.decorateSupplier(circuitBreaker, () -> {
                processWithExternalSystem(event);
                return null;
            })
        ).recover(CallNotPermittedException.class, e -> {
            // Circuit is open, queue for later
            delayedEventQueue.enqueue(event, Duration.ofMinutes(5));
            return null;
        }).get();
    }
}
```

**Event consumer patterns:**

| Pattern | Use Case |
|---------|----------|
| Idempotent | Prevent duplicate processing |
| Ordered | Maintain entity event order |
| Batched | Improve throughput |
| Async | Non-blocking processing |
| Circuit breaker | External system failures |

Reference: [ICM Event Framework](https://knowledge.intershop.com/kb/index.php/Display/2X3056)
