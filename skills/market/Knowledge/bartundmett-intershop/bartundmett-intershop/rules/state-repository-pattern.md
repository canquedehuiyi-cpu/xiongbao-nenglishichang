---
title: Use Repository Pattern for Business Object Access
impact: CRITICAL
impactDescription: ensures proper lifecycle management and testability
tags: state-management, repository, business-objects, architecture
---

## Use Repository Pattern for Business Object Access

**Impact: CRITICAL (ensures proper lifecycle management and testability)**

Repositories are the central entry point for creating, retrieving, and managing business objects. Always use repositories instead of direct persistent object access.

**Incorrect (direct PO access):**

```java
// Bad: Direct access to persistent objects
public class ProductService {

    @Inject
    private NamingMgr namingMgr;

    public ProductPO getProduct(String sku) {
        // Direct ORM access - breaks abstraction
        ProductPOKey key = new ProductPOKey(sku);
        return (ProductPO) namingMgr.lookupObject(ProductPO.class, key);
    }

    public void updateProduct(ProductPO product) {
        // Direct manipulation without validation
        product.setName("New Name");
        // No lifecycle hooks, no events, no validation
    }
}
```

**Correct (repository pattern):**

```java
// 1. Repository interface in capi package
public interface ProductRepository extends BusinessObjectRepository<ProductBO> {

    /**
     * Retrieves a product by SKU.
     * @param sku the product SKU
     * @return the product or null if not found
     */
    ProductBO getProductBySKU(String sku);

    /**
     * Finds products matching the given criteria.
     */
    List<ProductBO> findProducts(ProductSearchCriteria criteria);

    /**
     * Creates a new product.
     */
    ProductBO createProduct(ProductCreationData data);
}

// 2. Repository implementation in internal package
public class ProductRepositoryImpl implements ProductRepository {

    @Inject
    private NamingMgr namingMgr;

    @Inject
    private EventPublisher eventPublisher;

    @Override
    public ProductBO getProductBySKU(String sku) {
        ProductPOKey key = new ProductPOKey(sku);
        ProductPO po = (ProductPO) namingMgr.lookupObject(ProductPO.class, key);

        if (po == null) {
            return null;
        }

        // Wrap PO in BO for proper abstraction
        return new ProductBOImpl(po);
    }

    @Override
    public ProductBO createProduct(ProductCreationData data) {
        // Validation
        validateCreationData(data);

        // Create PO
        ProductPO po = (ProductPO) namingMgr.createObject(ProductPO.class);
        po.setSKU(data.getSku());
        po.setName(data.getName());

        // Wrap in BO
        ProductBO product = new ProductBOImpl(po);

        // Lifecycle event
        eventPublisher.publish(new ProductCreatedEvent(product));

        return product;
    }
}

// 3. Using the repository
public class ProductPipelet extends Pipelet {

    @Inject
    private ProductRepository productRepository;

    @Override
    public int execute(PipelineDictionary dict) {
        String sku = dict.get("SKU");

        // Good: Clean access through repository
        ProductBO product = productRepository.getProductBySKU(sku);

        if (product != null) {
            dict.put("Product", product);
        }

        return PIPELET_NEXT;
    }
}
```

**Repository design principles:**

| Principle | Description |
|-----------|-------------|
| Single Root Entity | One repository per aggregate root |
| Encapsulate Queries | All query logic inside repository |
| Return BOs, not POs | Never expose persistent objects |
| Lifecycle Management | Handle creation, validation, events |
| Testable | Easily mockable for unit tests |

**Aggregate pattern example:**

```java
// Order is the aggregate root
public interface OrderRepository extends BusinessObjectRepository<OrderBO> {
    OrderBO getOrder(String orderId);
    // OrderLineItems accessed via OrderBO, not separate repository
}

// Access line items through the aggregate root
OrderBO order = orderRepository.getOrder(orderId);
List<OrderLineItemBO> items = order.getLineItems();  // Not lineItemRepository.getItems(orderId)
```

Reference: [Guide - Business Objects](https://knowledge.intershop.com/kb/index.php/Display/U25993)
