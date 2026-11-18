---
title: Maintain Strict BO/PO Separation
impact: CRITICAL
impactDescription: ensures clean architecture and upgrade safety
tags: state-management, business-objects, persistent-objects, architecture, layering
---

## Maintain Strict BO/PO Separation

**Impact: CRITICAL (ensures clean architecture and upgrade safety)**

Business Objects (BOs) and Persistent Objects (POs) serve different purposes and must be kept strictly separated. BOs encapsulate business logic and form the public API, while POs handle database persistence.

**Incorrect (mixing BO and PO concerns):**

```java
// Bad: Exposing PO in public API
public interface ProductBO {
    // Leaking persistence implementation!
    ProductPO getPersistentObject();

    // Returning PO type in business method
    List<ProductPO> getRelatedProducts();
}

// Bad: Business logic in PO
public class ProductPO extends PersistentObjectPO {

    // Business logic doesn't belong in PO!
    public Money calculateDiscountedPrice(CustomerBO customer) {
        // This should be in ProductBO or a service
        if (customer.isVIP()) {
            return getBasePrice().multiply(0.9);
        }
        return getBasePrice();
    }
}
```

**Correct (clean separation):**

```java
// 1. Business Object Interface (capi package - public API)
public interface ProductBO extends BusinessObject {

    String getSKU();
    String getName();
    String getDescription();
    Money getBasePrice();

    // Business methods
    Money calculatePrice(PricingContext context);
    boolean isAvailable();
    List<ProductBO> getRelatedProducts();

    // Extension point
    <T extends BusinessObjectExtension<ProductBO>> T getExtension(Class<T> extensionClass);
}

// 2. Business Object Implementation (internal package)
public class ProductBOImpl extends AbstractPersistentObjectBO implements ProductBO {

    private final ProductPO delegate;

    @Inject
    private PricingService pricingService;

    public ProductBOImpl(ProductPO persistentObject) {
        super(persistentObject);
        this.delegate = persistentObject;
    }

    @Override
    public String getSKU() {
        return delegate.getSKU();
    }

    @Override
    public Money calculatePrice(PricingContext context) {
        // Business logic in BO implementation
        return pricingService.calculatePrice(this, context);
    }

    @Override
    public List<ProductBO> getRelatedProducts() {
        // Convert POs to BOs before returning
        return delegate.getRelatedProductPOs().stream()
            .map(ProductBOImpl::new)
            .collect(Collectors.toList());
    }

    // Never expose this publicly!
    ProductPO getDelegate() {
        return delegate;
    }
}

// 3. Persistent Object (orm package - database mapping)
@Entity
@Table(name = "PRODUCT")
public class ProductPO extends PersistentObjectPO {

    @Column(name = "SKU")
    private String sku;

    @Column(name = "NAME")
    private String name;

    @Column(name = "BASE_PRICE")
    private BigDecimal basePrice;

    // Only getters/setters for persistence
    // NO business logic here!

    public String getSKU() { return sku; }
    public void setSKU(String sku) { this.sku = sku; }

    // Relation to other POs (internal)
    @OneToMany
    public List<ProductPO> getRelatedProductPOs() { ... }
}
```

**Layer responsibilities:**

| Layer | Type | Purpose | Contains |
|-------|------|---------|----------|
| API | BO Interface | Public contract | Method signatures, no implementation |
| Business | BO Implementation | Business logic | Validation, calculations, workflows |
| Persistence | PO | Database mapping | CRUD operations, ORM annotations |

**Benefits of separation:**

- BOs can change implementation without affecting API consumers
- POs can be optimized for database performance
- Business logic is testable without database
- Multiple BO implementations possible (ORM, cache, mock)

Reference: [Concept - Business Objects](https://knowledge.intershop.com/kb/index.php/Display/2307B9)
