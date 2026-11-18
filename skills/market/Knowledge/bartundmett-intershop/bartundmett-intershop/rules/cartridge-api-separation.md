---
title: Separate API and Implementation Cartridges
impact: HIGH
impactDescription: enables clean architecture and flexible implementation swapping
tags: cartridge, architecture, api, implementation, separation
---

## Separate API and Implementation Cartridges

**Impact: HIGH (enables clean architecture and flexible implementation swapping)**

API cartridges define public interfaces while implementation cartridges provide the actual logic. This separation allows swapping implementations without affecting API consumers.

**Incorrect (mixing API and implementation):**

```
// Bad: Single cartridge with everything
bc_product/
├── javasource/
│   └── com/mycompany/product/
│       ├── ProductBO.java           // Interface
│       ├── ProductBOImpl.java       // Implementation (mixed!)
│       ├── ProductPO.java           // Persistent object (mixed!)
│       └── ProductRepository.java   // Both interface and impl
└── resources/
    └── ...
```

**Correct (separated cartridges):**

```
// API Cartridge: bc_product
bc_product/
├── javasource/
│   └── com/mycompany/product/
│       └── capi/                    // "capi" = Component API
│           ├── ProductBO.java       // Interface only
│           ├── ProductRepository.java // Interface only
│           ├── ProductExtension.java  // Extension interface
│           └── ProductSearchCriteria.java // Value objects
├── resources/
│   └── bc_product/
│       └── contracts.component      // Contract declarations
└── staticfiles/
    └── ...

// Implementation Cartridge: bc_product_orm
bc_product_orm/
├── javasource/
│   └── com/mycompany/product/
│       └── internal/                // Internal implementation
│           ├── ProductBOImpl.java   // BO implementation
│           ├── ProductRepositoryImpl.java // Repository impl
│           └── ProductExtensionImpl.java  // Extension impl
│       └── orm/                     // ORM layer
│           ├── ProductPO.java       // Persistent object
│           └── ProductPOFactory.java
├── resources/
│   └── bc_product_orm/
│       ├── objectgraph-local.properties  // Guice bindings
│       └── orm.component            // ORM configuration
└── staticfiles/
    └── ...
```

**API cartridge (bc_product) contents:**

```java
// capi/ProductBO.java - Public interface
package com.mycompany.product.capi;

public interface ProductBO extends BusinessObject {
    String getSKU();
    String getName();
    Money getPrice();
    boolean isAvailable();
}

// capi/ProductRepository.java - Repository interface
package com.mycompany.product.capi;

public interface ProductRepository extends BusinessObjectRepository<ProductBO> {
    ProductBO getProductBySKU(String sku);
    List<ProductBO> search(ProductSearchCriteria criteria);
    ProductBO createProduct(ProductCreationData data);
}

// contracts.component - Declares public contracts
<?xml version="1.0" encoding="UTF-8"?>
<components xmlns="http://www.intershop.com/component/2010">
    <contract name="ProductBO"
        interface="com.mycompany.product.capi.ProductBO"/>
    <contract name="ProductRepository"
        interface="com.mycompany.product.capi.ProductRepository"/>
</components>
```

**Implementation cartridge (bc_product_orm) contents:**

```java
// internal/ProductBOImpl.java - Implementation
package com.mycompany.product.internal;

public class ProductBOImpl extends AbstractPersistentObjectBO
    implements ProductBO {

    private final ProductPO delegate;

    public ProductBOImpl(ProductPO po) {
        super(po);
        this.delegate = po;
    }

    @Override
    public String getSKU() {
        return delegate.getSKU();
    }
    // ... other implementations
}

// internal/ProductRepositoryImpl.java - Repository implementation
package com.mycompany.product.internal;

public class ProductRepositoryImpl implements ProductRepository {

    @Inject
    private NamingMgr namingMgr;

    @Override
    public ProductBO getProductBySKU(String sku) {
        ProductPO po = findProductPO(sku);
        return po != null ? new ProductBOImpl(po) : null;
    }
}

// objectgraph-local.properties - Guice bindings
local.modules=com.mycompany.product.internal.ProductModule

// ProductModule.java - Guice module
public class ProductModule extends AbstractModule {
    @Override
    protected void configure() {
        bind(ProductRepository.class).to(ProductRepositoryImpl.class);
    }
}
```

**Benefits of separation:**

| Benefit | Description |
|---------|-------------|
| Clear contracts | Consumers only depend on interfaces |
| Swappable implementations | Can replace ORM impl with cache impl |
| Testability | Easy to mock interfaces |
| Upgrade safety | Impl changes don't break consumers |
| Dependency management | Impl dependencies isolated |

Reference: [Concept - Cartridge](https://knowledge.intershop.com/kb/index.php/Display/308Z99)
