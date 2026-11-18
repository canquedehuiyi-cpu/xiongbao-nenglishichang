---
title: Use Optimistic Locking for Concurrent Updates
impact: HIGH
impactDescription: prevents lost updates in concurrent scenarios
tags: database, concurrency, locking, optimistic-locking
---

## Use Optimistic Locking for Concurrent Updates

**Impact: HIGH (prevents lost updates in concurrent scenarios)**

Use version-based optimistic locking to detect and handle concurrent modifications without holding database locks.

**Incorrect (no concurrency handling):**

```java
// Bad: Lost update problem
// User A: reads order (quantity=5)
// User B: reads order (quantity=5)
// User A: sets quantity=3, saves
// User B: sets quantity=7, saves (overwrites A's change!)

public void updateOrderQuantity(String orderId, int newQuantity) {
    OrderPO order = orderRepository.findById(orderId);
    order.setQuantity(newQuantity);
    orderRepository.save(order);  // No concurrency check!
}

// Bad: Pessimistic locking (holds lock, reduces throughput)
public void updateOrderQuantity(String orderId, int newQuantity) {
    OrderPO order = orderRepository.findByIdWithLock(orderId);  // SELECT FOR UPDATE
    // Other transactions blocked until this completes!
    order.setQuantity(newQuantity);
    orderRepository.save(order);
}
```

**Correct (optimistic locking):**

```java
// Good: Persistent object with version field
@Entity
@Table(name = "ORDER_LINE_ITEM")
public class OrderLineItemPO extends PersistentObjectPO {

    @Version
    @Column(name = "OCA")  // Optimistic Concurrency Attribute
    private long version;

    @Column(name = "QUANTITY")
    private int quantity;

    @Column(name = "UNIT_PRICE")
    private BigDecimal unitPrice;

    // Getters and setters
    public long getVersion() { return version; }
    // Version is managed by JPA, no setter needed
}

// Good: Handle optimistic lock exception
public class OrderService {

    private static final int MAX_RETRIES = 3;

    public void updateOrderQuantity(String orderId, String lineItemId, int newQuantity) {
        int attempts = 0;

        while (attempts < MAX_RETRIES) {
            try {
                doUpdateQuantity(orderId, lineItemId, newQuantity);
                return;  // Success
            } catch (OptimisticLockException e) {
                attempts++;
                logger.warn("Concurrent modification detected, retrying",
                    kv("orderId", orderId),
                    kv("attempt", attempts));

                if (attempts >= MAX_RETRIES) {
                    throw new ConcurrentModificationException(
                        "Failed to update after " + MAX_RETRIES + " attempts", e);
                }

                // Small delay before retry
                sleep(100 * attempts);
            }
        }
    }

    @Transactional
    private void doUpdateQuantity(String orderId, String lineItemId, int newQuantity) {
        OrderLineItemPO lineItem = lineItemRepository.findById(lineItemId);

        // Validate business rules with fresh data
        validateQuantityChange(lineItem, newQuantity);

        lineItem.setQuantity(newQuantity);
        lineItemRepository.save(lineItem);
        // If version changed since read, OptimisticLockException thrown
    }
}
```

**Version in REST API:**

```java
// Good: Include version in API for client-side tracking
public class LineItemRO {
    private String id;
    private int quantity;
    private long version;  // Send version to client
}

@PUT
@Path("/orders/{orderId}/items/{itemId}")
public Response updateLineItem(
        @PathParam("orderId") String orderId,
        @PathParam("itemId") String itemId,
        LineItemUpdateRO update) {

    // Client must send back the version they have
    if (update.getVersion() == null) {
        return Response.status(Response.Status.BAD_REQUEST)
            .entity(new ErrorRO("Version required for update"))
            .build();
    }

    try {
        LineItemBO updated = orderService.updateLineItem(
            orderId, itemId, update.getQuantity(), update.getVersion());
        return Response.ok(mapper.toRO(updated)).build();

    } catch (OptimisticLockException e) {
        // HTTP 409 Conflict
        return Response.status(Response.Status.CONFLICT)
            .entity(new ErrorRO("CONCURRENT_MODIFICATION",
                "This item was modified by another user. Please refresh and try again."))
            .build();
    }
}
```

**Conditional update pattern:**

```java
// Good: Update only if version matches
@Modifying
@Query("UPDATE OrderLineItemPO o SET o.quantity = :quantity " +
       "WHERE o.id = :id AND o.version = :expectedVersion")
int updateQuantityIfVersionMatches(
    @Param("id") String id,
    @Param("quantity") int quantity,
    @Param("expectedVersion") long expectedVersion);

// Usage
int updatedRows = repository.updateQuantityIfVersionMatches(itemId, newQuantity, version);
if (updatedRows == 0) {
    throw new OptimisticLockException("Item was modified concurrently");
}
```

**When to use each approach:**

| Scenario | Approach | Reason |
|----------|----------|--------|
| Shopping cart updates | Optimistic | High concurrency, short lock |
| Inventory reservation | Pessimistic | Critical accuracy needed |
| User profile update | Optimistic | Low conflict probability |
| Bank transfer | Pessimistic | Must not lose updates |
| Order submission | Optimistic + retry | User can retry |

Reference: [JPA Optimistic Locking](https://docs.oracle.com/javaee/7/tutorial/persistence-locking.htm)
