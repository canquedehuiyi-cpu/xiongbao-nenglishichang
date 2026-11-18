---
title: Optimize Database Queries
impact: CRITICAL
impactDescription: 2-50× improvement in response times
tags: performance, database, queries, optimization, ORM
---

## Optimize Database Queries

**Impact: CRITICAL (2-50× improvement in response times)**

Database queries are often the primary bottleneck in ICM applications. Use efficient query patterns, proper indexing hints, and avoid N+1 query problems.

**Incorrect (N+1 query problem):**

```java
// Bad: N+1 queries - one query per product in loop
public List<ProductDTO> getProductsWithPrices(Collection<String> skus) {
    List<ProductDTO> results = new ArrayList<>();

    for (String sku : skus) {
        // Query 1: Get product
        ProductBO product = productRepository.getProduct(sku);

        // Query 2: Get price (per product!)
        PriceBO price = priceRepository.getPrice(product);

        // Query 3: Get stock (per product!)
        StockBO stock = stockRepository.getStock(product);

        results.add(new ProductDTO(product, price, stock));
    }

    return results;  // Total: 1 + (3 × N) queries!
}
```

**Correct (batch queries):**

```java
// Good: Batch queries - constant number of queries regardless of size
public List<ProductDTO> getProductsWithPrices(Collection<String> skus) {
    // Query 1: Get all products in one query
    Map<String, ProductBO> products = productRepository.getProductsBySKUs(skus);

    // Query 2: Get all prices in one query
    Map<String, PriceBO> prices = priceRepository.getPricesForProducts(products.keySet());

    // Query 3: Get all stocks in one query
    Map<String, StockBO> stocks = stockRepository.getStocksForProducts(products.keySet());

    // Combine in memory
    return skus.stream()
        .map(sku -> new ProductDTO(
            products.get(sku),
            prices.get(sku),
            stocks.get(sku)
        ))
        .collect(Collectors.toList());  // Total: 3 queries regardless of N
}
```

**Query optimization patterns:**

```java
// 1. Use projections for read-only data
public interface ProductProjection {
    String getSKU();
    String getName();
    BigDecimal getPrice();
}

// Instead of loading full ProductBO with all relations
List<ProductProjection> products = query.select(ProductProjection.class)
    .from(ProductPO.class)
    .where("category.id = ?", categoryId)
    .list();

// 2. Use pagination for large result sets
public class ProductQueryService {

    public PagedResult<ProductBO> searchProducts(SearchCriteria criteria, int page, int pageSize) {
        Query query = createQuery(criteria);

        // Set limits to avoid loading all results
        query.setFirstResult(page * pageSize);
        query.setMaxResults(pageSize);

        List<ProductBO> products = query.list();
        long totalCount = query.count();

        return new PagedResult<>(products, page, pageSize, totalCount);
    }
}

// 3. Use query hints for better execution plans
Query query = queryMgr.createQuery();
query.setHint("index", "IDX_PRODUCT_CATEGORY");  // Suggest index usage
query.setHint("fetchSize", 100);  // Optimize fetch size

// 4. Avoid SELECT * - specify needed columns
String hql = "SELECT p.sku, p.name, p.price FROM ProductPO p WHERE p.active = true";
// Instead of: "FROM ProductPO p WHERE p.active = true"
```

**Common anti-patterns to avoid:**

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| N+1 queries | O(N) database calls | Batch fetching |
| SELECT * | Loads unnecessary data | Projections |
| No pagination | Memory issues | LIMIT/OFFSET |
| Missing indexes | Full table scans | Query hints, DBA review |
| Lazy loading in loops | Hidden N+1 | Eager fetch or batch |

Reference: [Overview - Persistent Object Layer](https://support.intershop.com/kb/index.php/Display/278Z46)
