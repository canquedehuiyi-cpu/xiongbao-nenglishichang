---
title: Use Lazy Loading for Related Entities
impact: HIGH
impactDescription: reduces initial query time and memory usage
tags: performance, lazy-loading, orm, optimization
---

## Use Lazy Loading for Related Entities

**Impact: HIGH (reduces initial query time and memory usage)**

Load related entities only when needed. Eager loading entire object graphs causes performance issues and memory pressure.

**Incorrect (eager loading everything):**

```java
// Bad: Eager loading all relations
@Entity
public class OrderPO {

    @OneToMany(fetch = FetchType.EAGER)  // Loads ALL line items
    private List<OrderLineItemPO> lineItems;

    @ManyToOne(fetch = FetchType.EAGER)  // Loads customer with every order
    private CustomerPO customer;

    @OneToMany(fetch = FetchType.EAGER)  // Loads ALL shipments
    private List<ShipmentPO> shipments;

    @OneToMany(fetch = FetchType.EAGER)  // Loads ALL payment records
    private List<PaymentPO> payments;
}

// Result: Simple order lookup loads 100s of related objects!
// Even if you only need the order status
```

**Correct (lazy loading with explicit fetching):**

```java
// Good: Default to lazy loading
@Entity
public class OrderPO {

    @OneToMany(fetch = FetchType.LAZY)  // Load only when accessed
    private List<OrderLineItemPO> lineItems;

    @ManyToOne(fetch = FetchType.LAZY)
    private CustomerPO customer;

    @OneToMany(fetch = FetchType.LAZY)
    private List<ShipmentPO> shipments;

    @OneToMany(fetch = FetchType.LAZY)
    private List<PaymentPO> payments;
}

// Good: Repository with specific fetch strategies
public class OrderRepositoryImpl implements OrderRepository {

    // Basic order lookup - no relations loaded
    @Override
    public OrderBO getOrder(String orderId) {
        OrderPO po = queryManager.get(OrderPO.class, orderId);
        return po != null ? new OrderBOImpl(po) : null;
    }

    // Order with line items for cart display
    @Override
    public OrderBO getOrderWithLineItems(String orderId) {
        String hql = "SELECT DISTINCT o FROM OrderPO o " +
                     "LEFT JOIN FETCH o.lineItems " +
                     "WHERE o.id = :orderId";
        OrderPO po = queryManager.createQuery(hql)
            .setParameter("orderId", orderId)
            .uniqueResult();
        return po != null ? new OrderBOImpl(po) : null;
    }

    // Full order for order detail page
    @Override
    public OrderBO getOrderWithDetails(String orderId) {
        String hql = "SELECT DISTINCT o FROM OrderPO o " +
                     "LEFT JOIN FETCH o.lineItems li " +
                     "LEFT JOIN FETCH li.product " +
                     "LEFT JOIN FETCH o.customer " +
                     "LEFT JOIN FETCH o.shipments " +
                     "WHERE o.id = :orderId";
        OrderPO po = queryManager.createQuery(hql)
            .setParameter("orderId", orderId)
            .uniqueResult();
        return po != null ? new OrderBOImpl(po) : null;
    }

    // Orders list - no relations needed
    @Override
    public List<OrderBO> getRecentOrders(String customerId, int limit) {
        String hql = "FROM OrderPO o WHERE o.customer.id = :customerId " +
                     "ORDER BY o.createdDate DESC";
        return queryManager.createQuery(hql)
            .setParameter("customerId", customerId)
            .setMaxResults(limit)
            .list()
            .stream()
            .map(OrderBOImpl::new)
            .collect(Collectors.toList());
    }
}
```

**Handling lazy loading in business layer:**

```java
// Good: BO provides lazy access with null safety
public class OrderBOImpl implements OrderBO {

    private final OrderPO delegate;

    @Override
    public List<OrderLineItemBO> getLineItems() {
        // Lazy loading triggered here if not already loaded
        return delegate.getLineItems().stream()
            .map(OrderLineItemBOImpl::new)
            .collect(Collectors.toList());
    }

    @Override
    public int getLineItemCount() {
        // Avoid loading full collection just for count
        if (Hibernate.isInitialized(delegate.getLineItems())) {
            return delegate.getLineItems().size();
        }
        // Query for count instead
        return orderRepository.getLineItemCount(delegate.getId());
    }
}

// Good: Service chooses appropriate loading strategy
public class OrderDisplayService {

    public OrderSummaryDTO getOrderSummary(String orderId) {
        // Light load - no relations needed
        OrderBO order = orderRepository.getOrder(orderId);
        return OrderSummaryDTO.builder()
            .orderId(order.getId())
            .status(order.getStatus())
            .total(order.getTotal())
            .createdDate(order.getCreatedDate())
            .build();
    }

    public OrderDetailDTO getOrderDetail(String orderId) {
        // Full load - needs all details
        OrderBO order = orderRepository.getOrderWithDetails(orderId);
        return mapToDetailDTO(order);
    }
}
```

**Avoiding LazyInitializationException:**

```java
// Bad: Accessing lazy property outside transaction
public OrderDTO getOrder(String orderId) {
    OrderBO order = orderRepository.getOrder(orderId);  // Transaction ends
    return OrderDTO.builder()
        .lineItems(order.getLineItems())  // LazyInitializationException!
        .build();
}

// Good: Load within transaction or use DTO projection
@Transactional(readOnly = true)
public OrderDTO getOrder(String orderId) {
    OrderBO order = orderRepository.getOrderWithLineItems(orderId);
    return OrderDTO.builder()
        .lineItems(order.getLineItems())  // Already loaded
        .build();
}

// Good: Or use DTO projection query
public OrderDTO getOrder(String orderId) {
    return queryManager.createQuery(
        "SELECT new OrderDTO(o.id, o.status, o.total) " +
        "FROM OrderPO o WHERE o.id = :id")
        .setParameter("id", orderId)
        .uniqueResult();
}
```

**Loading strategy decision matrix:**

| Use Case | Strategy | Reason |
|----------|----------|--------|
| List view | Lazy (no fetch) | Only need basic fields |
| Detail view | Eager (join fetch) | Need all related data |
| Count only | Lazy + count query | Avoid loading entities |
| Conditional | Lazy + check | Load only if needed |
| Batch processing | Batch fetch | Efficient bulk loading |

Reference: [JPA Fetching Strategies](https://docs.oracle.com/javaee/7/tutorial/persistence-criteria003.htm)
