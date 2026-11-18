---
title: Use Caching for Expensive Operations
impact: CRITICAL
impactDescription: 10-100× improvement for repeated queries
tags: performance, caching, optimization, scalability
---

## Use Caching for Expensive Operations

**Impact: CRITICAL (10-100× improvement for repeated queries)**

Expensive database queries, external service calls, and computed results should be cached at the appropriate level. ICM provides multiple caching mechanisms depending on the scope and lifetime of the data.

**Incorrect (repeated expensive operations):**

```java
// Bad: Fetching same data multiple times per request
public class ProductDetailsPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        String sku = dict.get("SKU");

        // Each call queries the database
        ProductBO product = productRepository.getProduct(sku);
        CategoryBO category = categoryRepository.getCategory(product.getCategoryID());
        PriceBO price = priceService.calculatePrice(product);
        StockBO stock = stockService.getStock(product);

        // Later in the same request, same data fetched again
        if (product.isConfigurable()) {
            // Another database query for the same product!
            ProductBO sameProduct = productRepository.getProduct(sku);
            // ...
        }

        return PIPELET_NEXT;
    }
}
```

**Correct (using appropriate caching):**

```java
// 1. Per-request caching with pipeline dictionary
public class ProductDetailsPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        String sku = dict.get("SKU");

        // Cache key for this request
        String cacheKey = "ProductDetails:" + sku;

        // Check if already fetched in this request
        ProductDetails details = dict.get(cacheKey);
        if (details == null) {
            details = fetchProductDetails(sku);
            dict.put(cacheKey, details);  // Good: Cache for this request
        }

        return PIPELET_NEXT;
    }
}

// 2. Cross-request caching with CacheMgr
@Inject
private CacheMgr cacheMgr;

public ProductBO getProduct(String sku) {
    Cache cache = cacheMgr.getCache("ProductCache");
    String cacheKey = "product:" + sku;

    ProductBO product = cache.get(cacheKey);
    if (product == null) {
        product = productRepository.getProduct(sku);
        cache.put(cacheKey, product, 300);  // Good: Cache for 5 minutes
    }
    return product;
}

// 3. For computed/expensive operations, use memoization
public class PriceCalculationService {

    private final Cache priceCache;

    @Inject
    public PriceCalculationService(CacheMgr cacheMgr) {
        this.priceCache = cacheMgr.getCache("PriceCache");
    }

    public Money calculateComplexPrice(ProductBO product, CustomerBO customer) {
        String cacheKey = buildCacheKey(product, customer);

        return priceCache.computeIfAbsent(cacheKey, () -> {
            // Expensive calculation only runs once per cache period
            return performComplexPriceCalculation(product, customer);
        });
    }
}
```

**Cache invalidation strategies:**

```java
// Event-based invalidation
public class ProductUpdateHandler {

    @Inject
    private CacheMgr cacheMgr;

    public void onProductUpdated(ProductBO product) {
        Cache cache = cacheMgr.getCache("ProductCache");
        cache.remove("product:" + product.getSKU());
        cache.remove("productDetails:" + product.getSKU());
    }
}
```

**Caching levels in ICM:**

| Level | Scope | Use Case |
|-------|-------|----------|
| Pipeline Dictionary | Single request | Avoid duplicate queries in one request |
| CacheMgr | Cross-request | Product data, configurations |
| Redis/External | Cross-node | Session data, distributed caching |

Reference: [Concept - Technical Architecture of ICM 11+](https://knowledge.intershop.com/kb/index.php/Display/30983L)
