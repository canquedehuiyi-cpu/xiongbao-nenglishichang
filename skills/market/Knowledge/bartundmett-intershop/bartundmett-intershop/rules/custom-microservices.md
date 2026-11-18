---
title: Prefer Microservices for Complex Customizations
impact: CRITICAL
impactDescription: reduces coupling and enables independent deployment
tags: customization, microservices, architecture, scalability
---

## Prefer Microservices for Complex Customizations

**Impact: CRITICAL (reduces coupling and enables independent deployment)**

Additional microservices are the recommended approach for extending the Intershop Commerce Platform. They can provide additional REST APIs, handle business events, or integrate with external systems without modifying the ICM core.

**Incorrect (implementing everything inside ICM):**

```java
// Bad: Complex integration logic inside ICM cartridge
public class ExternalERPSyncPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        Order order = dict.get("Order");

        // Complex ERP integration logic directly in pipelet
        ERPClient client = new ERPClient(getERPConfig());
        ERPOrder erpOrder = transformToERPFormat(order);

        try {
            client.connect();
            client.authenticate();
            client.submitOrder(erpOrder);
            client.waitForConfirmation();
            order.setERPOrderID(erpOrder.getConfirmationID());
        } finally {
            client.disconnect();
        }

        return PIPELET_NEXT;
    }
}
```

**Correct (microservice architecture):**

```java
// ICM side - simple REST call to microservice
public class ERPIntegrationPipelet extends Pipelet {

    @Inject
    private ERPIntegrationService erpService;

    @Override
    public int execute(PipelineDictionary dict) {
        Order order = dict.get("Order");

        // Simple async call to microservice
        erpService.submitOrderAsync(order.getOrderID());

        return PIPELET_NEXT;
    }
}

// Microservice (separate project/container)
@RestController
@RequestMapping("/api/erp")
public class ERPOrderController {

    @Autowired
    private ERPClient erpClient;

    @Autowired
    private OrderEventPublisher eventPublisher;

    @PostMapping("/orders/{orderId}")
    public ResponseEntity<ERPResult> submitOrder(@PathVariable String orderId) {
        // All complex ERP logic in dedicated microservice
        Order order = fetchOrderFromICM(orderId);
        ERPOrder erpOrder = transformToERPFormat(order);

        ERPResult result = erpClient.submit(erpOrder);

        // Publish event for ICM to consume
        eventPublisher.publishOrderSubmitted(orderId, result);

        return ResponseEntity.ok(result);
    }
}
```

**When to use microservices:**

| Use Case | Microservice | ICM Cartridge |
|----------|--------------|---------------|
| Complex external integrations | Yes | |
| Long-running processes | Yes | |
| Compute-intensive operations | Yes | |
| Simple business logic extension | | Yes |
| UI customizations | | Yes |
| Core commerce modifications | | Good: (via extensions) |

**Benefits:**
- Independent deployment and scaling
- Technology flexibility (not limited to Java)
- Easier testing and debugging
- Reduced ICM upgrade complexity
- Better fault isolation

Reference: [Guide - Intershop Commerce Platform - Customization Options](https://knowledge.intershop.com/kb/index.php/Display/29230E)
