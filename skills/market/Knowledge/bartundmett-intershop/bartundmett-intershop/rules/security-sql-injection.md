---
title: Use Parameterized Queries to Prevent SQL Injection
impact: CRITICAL
impactDescription: prevents SQL injection attacks
tags: security, sql-injection, database, queries, parameterized
---

## Use Parameterized Queries to Prevent SQL Injection

**Impact: CRITICAL (prevents SQL injection attacks)**

Never concatenate user input into SQL queries. Always use parameterized queries or ICM's query builder with proper parameter binding.

**Incorrect (SQL injection vulnerability):**

```java
// Bad: CRITICAL VULNERABILITY: String concatenation in SQL
public List<ProductBO> searchProducts(String name) {
    // Attacker can inject: "'; DROP TABLE products; --"
    String sql = "SELECT * FROM Product WHERE name LIKE '%" + name + "%'";
    return queryManager.executeQuery(sql);
}

// Bad: CRITICAL VULNERABILITY: Dynamic ORDER BY
public List<OrderBO> getOrders(String sortColumn) {
    // Attacker can inject: "status; DELETE FROM orders; --"
    String sql = "SELECT * FROM orders ORDER BY " + sortColumn;
    return queryManager.executeQuery(sql);
}

// Bad: CRITICAL VULNERABILITY: IN clause with concatenation
public List<ProductBO> getProductsByIds(List<String> ids) {
    // Attacker can manipulate IDs list
    String idList = String.join("','", ids);
    String sql = "SELECT * FROM Product WHERE id IN ('" + idList + "')";
    return queryManager.executeQuery(sql);
}
```

**Correct (parameterized queries):**

```java
// Good: Named parameters
public List<ProductBO> searchProducts(String name) {
    String hql = "FROM ProductPO p WHERE p.name LIKE :namePattern";

    Query query = queryManager.createQuery(hql);
    query.setParameter("namePattern", "%" + sanitizeWildcard(name) + "%");

    return query.list();
}

// Good: Positional parameters
public ProductBO getProduct(String sku) {
    String hql = "FROM ProductPO p WHERE p.sku = ?1";

    Query query = queryManager.createQuery(hql);
    query.setParameter(1, sku);

    return (ProductBO) query.uniqueResult();
}

// Good: Safe IN clause
public List<ProductBO> getProductsByIds(List<String> ids) {
    if (ids == null || ids.isEmpty()) {
        return Collections.emptyList();
    }

    String hql = "FROM ProductPO p WHERE p.id IN (:ids)";

    Query query = queryManager.createQuery(hql);
    query.setParameterList("ids", ids);

    return query.list();
}

// Good: Whitelist for ORDER BY columns
public List<OrderBO> getOrders(String sortColumn, boolean ascending) {
    // Whitelist allowed columns
    Set<String> allowedColumns = Set.of("createdDate", "status", "total", "customerName");

    if (!allowedColumns.contains(sortColumn)) {
        sortColumn = "createdDate";  // Default to safe value
    }

    String direction = ascending ? "ASC" : "DESC";

    // Safe because sortColumn is from whitelist
    String hql = "FROM OrderPO o ORDER BY o." + sortColumn + " " + direction;

    return queryManager.createQuery(hql).list();
}

// Good: Using Criteria API (fully parameterized)
public List<ProductBO> searchProductsCriteria(ProductSearchCriteria criteria) {
    CriteriaBuilder cb = entityManager.getCriteriaBuilder();
    CriteriaQuery<ProductPO> query = cb.createQuery(ProductPO.class);
    Root<ProductPO> product = query.from(ProductPO.class);

    List<Predicate> predicates = new ArrayList<>();

    if (criteria.getName() != null) {
        predicates.add(cb.like(product.get("name"), "%" + criteria.getName() + "%"));
    }

    if (criteria.getMinPrice() != null) {
        predicates.add(cb.ge(product.get("price"), criteria.getMinPrice()));
    }

    if (criteria.getCategoryId() != null) {
        predicates.add(cb.equal(product.get("category").get("id"), criteria.getCategoryId()));
    }

    query.where(predicates.toArray(new Predicate[0]));

    return entityManager.createQuery(query).getResultList();
}
```

**Helper for wildcard sanitization:**

```java
// Good: Sanitize LIKE wildcards in user input
public static String sanitizeWildcard(String input) {
    if (input == null) {
        return "";
    }
    // Escape SQL LIKE special characters
    return input
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_");
}
```

**Prevention checklist:**

| Check | Safe | Unsafe |
|-------|------|--------|
| Column values | `?` or `:param` | `+ userInput +` |
| IN clauses | `setParameterList()` | String.join() |
| ORDER BY | Whitelist columns | Dynamic column names |
| LIKE patterns | Escape wildcards | Raw user input |
| Table names | Never dynamic | Dynamic from input |

Reference: [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
