---
title: Manage Persistent Object Lifecycle
impact: MEDIUM-HIGH
impactDescription: prevents data corruption and improves performance
tags: database, persistence, po, lifecycle, orm
---

## Manage Persistent Object Lifecycle

**Impact: MEDIUM-HIGH (prevents data corruption and improves performance)**

Understanding and properly managing persistent object states (transient, persistent, detached) is essential for correct data handling and avoiding common ORM pitfalls.

**Incorrect (mismanaged PO lifecycle):**

```java
// Bad: Modifying detached entity without reattaching
public void updateProduct(ProductUpdateData data) {
    ProductPO product = productRepository.findById(data.getId());  // Now detached
    // ... later, in different transaction context
    product.setName(data.getName());  // Modifying detached entity!
    // Changes never persisted
}

// Bad: Returning managed entities outside transaction
@Transactional
public ProductPO getProduct(String id) {
    return em.find(ProductPO.class, id);  // Returns managed entity
}
// Entity becomes detached after method returns, lazy loading fails

// Bad: Mixing managed entities from different contexts
public void copyProduct(String sourceId, String targetId) {
    ProductPO source = em1.find(ProductPO.class, sourceId);  // Context 1
    ProductPO target = em2.find(ProductPO.class, targetId);  // Context 2

    target.setCategory(source.getCategory());  // Different contexts!
}

// Bad: Not handling merge properly
public void updateProduct(ProductPO detachedProduct) {
    em.persist(detachedProduct);  // Error! Entity already has ID
}
```

**Correct (proper lifecycle management):**

```java
// Good: Transaction-scoped entity management
@Injectable
public class ProductRepository {

    @Inject
    private EntityManager em;

    @Transactional
    public ProductBO updateProduct(String id, ProductUpdateData data) {
        // Find within transaction - entity is managed
        ProductPO product = em.find(ProductPO.class, id);

        if (product == null) {
            throw new EntityNotFoundException("Product not found: " + id);
        }

        // Modify managed entity - changes auto-flushed
        product.setName(data.getName());
        product.setDescription(data.getDescription());
        product.setLastModified(Instant.now());

        // No explicit save needed - dirty checking handles it
        return productMapper.toBO(product);
    }

    @Transactional
    public ProductBO mergeProduct(ProductPO detachedProduct) {
        // Use merge for detached entities
        ProductPO managed = em.merge(detachedProduct);
        return productMapper.toBO(managed);
    }
}

// Good: Proper fetch strategy for use outside transaction
@Injectable
public class ProductService {

    @Inject
    private ProductRepository productRepository;

    @Transactional(readOnly = true)
    public ProductBO getProductWithDetails(String id) {
        ProductPO product = em.find(ProductPO.class, id);

        // Force initialization of lazy collections within transaction
        Hibernate.initialize(product.getAttributes());
        Hibernate.initialize(product.getImages());

        return productMapper.toBO(product);  // BO is safe to use outside
    }

    // Or use fetch joins
    @Transactional(readOnly = true)
    public ProductBO getProductWithCategory(String id) {
        ProductPO product = em.createQuery(
            "SELECT p FROM ProductPO p " +
            "JOIN FETCH p.category " +
            "JOIN FETCH p.brand " +
            "WHERE p.id = :id", ProductPO.class)
            .setParameter("id", id)
            .getSingleResult();

        return productMapper.toBO(product);
    }
}

// Good: Explicit state transitions
@Injectable
public class EntityStateManager {

    @Inject
    private EntityManager em;

    public <T> T reattach(T detachedEntity) {
        // Merge returns managed copy
        return em.merge(detachedEntity);
    }

    public <T> void refresh(T managedEntity) {
        // Reload from database
        em.refresh(managedEntity);
    }

    public <T> void detach(T managedEntity) {
        // Explicitly detach from context
        em.detach(managedEntity);
    }

    public boolean isManaged(Object entity) {
        return em.contains(entity);
    }

    public EntityState getState(Object entity) {
        PersistenceUnitUtil util = em.getEntityManagerFactory()
            .getPersistenceUnitUtil();

        if (entity == null) {
            return EntityState.TRANSIENT;
        }

        Object id = util.getIdentifier(entity);

        if (id == null) {
            return EntityState.TRANSIENT;
        }

        if (em.contains(entity)) {
            return EntityState.MANAGED;
        }

        return EntityState.DETACHED;
    }
}

// Good: Safe entity copying
@Injectable
public class ProductCopyService {

    @Inject
    private EntityManager em;

    @Transactional
    public ProductPO copyProduct(String sourceId) {
        ProductPO source = em.find(ProductPO.class, sourceId);

        // Create new transient entity
        ProductPO copy = new ProductPO();
        copy.setName(source.getName() + " (Copy)");
        copy.setDescription(source.getDescription());
        copy.setSku(generateNewSku());

        // For associations, reference the same managed entity
        copy.setCategory(source.getCategory());  // Same context, OK

        // For collections, create new collection with copied items
        copy.setAttributes(source.getAttributes().stream()
            .map(attr -> copyAttribute(attr, copy))
            .collect(toList()));

        em.persist(copy);  // Transient -> Managed
        return copy;
    }

    private AttributePO copyAttribute(AttributePO source, ProductPO newParent) {
        AttributePO copy = new AttributePO();
        copy.setName(source.getName());
        copy.setValue(source.getValue());
        copy.setProduct(newParent);
        return copy;  // Will be persisted via cascade
    }
}

// Good: Batch operations with proper lifecycle
@Injectable
public class ProductBatchService {

    @Inject
    private EntityManager em;

    @Transactional
    public int updatePrices(String categoryId, BigDecimal multiplier) {
        // Bulk update avoids loading entities
        return em.createQuery(
            "UPDATE ProductPO p SET p.price = p.price * :multiplier " +
            "WHERE p.category.id = :categoryId")
            .setParameter("multiplier", multiplier)
            .setParameter("categoryId", categoryId)
            .executeUpdate();

        // Note: Managed entities in context may be stale after bulk update
        // Clear context if you need to reload
        // em.clear();
    }

    @Transactional
    public void batchUpdate(List<ProductUpdateData> updates) {
        int count = 0;

        for (ProductUpdateData data : updates) {
            ProductPO product = em.find(ProductPO.class, data.getId());
            product.setName(data.getName());
            product.setPrice(data.getPrice());

            if (++count % 50 == 0) {
                em.flush();  // Execute pending SQL
                em.clear();  // Detach all entities, free memory
            }
        }
    }
}
```

**Entity states:**

| State | In Context | Has ID | Database Sync |
|-------|-----------|--------|---------------|
| Transient | No | No | Not synced |
| Managed | Yes | Yes | Auto-synced |
| Detached | No | Yes | Manual merge |
| Removed | Yes | Yes | Will delete |

Reference: [JPA Entity Lifecycle](https://knowledge.intershop.com/kb/index.php/Display/2Y3817)
