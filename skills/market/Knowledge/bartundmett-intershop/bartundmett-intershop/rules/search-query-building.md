---
title: Build Search Queries Safely
impact: MEDIUM
impactDescription: prevents query injection and improves reliability
tags: search, query, solr, security
---

## Build Search Queries Safely

**Impact: MEDIUM (prevents query injection and improves reliability)**

Search queries built from user input must be properly escaped and validated to prevent query injection attacks and unexpected behavior.

**Incorrect (unsafe query building):**

```java
// Bad: Direct user input in query
public SearchResult search(String userQuery) {
    String query = "name:" + userQuery;  // Injection risk!
    return solrClient.query(new SolrQuery(query));
}

// Bad: Building complex queries with string concatenation
public SearchResult advancedSearch(Map<String, String> criteria) {
    StringBuilder query = new StringBuilder();
    for (Map.Entry<String, String> entry : criteria.entrySet()) {
        query.append(entry.getKey())
             .append(":")
             .append(entry.getValue())  // Not escaped!
             .append(" AND ");
    }
    return solrClient.query(new SolrQuery(query.toString()));
}

// Bad: No validation of field names
public SearchResult searchByField(String fieldName, String value) {
    String query = fieldName + ":" + value;  // fieldName could be malicious!
    return solrClient.query(new SolrQuery(query));
}
```

**Correct (safe query building):**

```java
// Good: Use query builder pattern
@Injectable
public class SearchQueryBuilder {

    private final List<String> clauses = new ArrayList<>();
    private final List<String> filterQueries = new ArrayList<>();
    private final Map<String, Float> fieldBoosts = new HashMap<>();

    public SearchQueryBuilder term(String field, String value) {
        if (StringUtils.isNotBlank(value) && isValidField(field)) {
            String escaped = ClientUtils.escapeQueryChars(value);
            clauses.add(field + ":" + escaped);
        }
        return this;
    }

    public SearchQueryBuilder phrase(String field, String value) {
        if (StringUtils.isNotBlank(value) && isValidField(field)) {
            String escaped = ClientUtils.escapeQueryChars(value);
            clauses.add(field + ":\"" + escaped + "\"");
        }
        return this;
    }

    public SearchQueryBuilder range(String field, Object min, Object max) {
        if (isValidField(field)) {
            String minStr = min != null ? min.toString() : "*";
            String maxStr = max != null ? max.toString() : "*";
            clauses.add(field + ":[" + minStr + " TO " + maxStr + "]");
        }
        return this;
    }

    public SearchQueryBuilder filter(String field, String value) {
        if (StringUtils.isNotBlank(value) && isValidField(field)) {
            String escaped = ClientUtils.escapeQueryChars(value);
            filterQueries.add(field + ":" + escaped);
        }
        return this;
    }

    public SearchQueryBuilder boost(String field, float boost) {
        if (isValidField(field)) {
            fieldBoosts.put(field, boost);
        }
        return this;
    }

    public SolrQuery build() {
        SolrQuery query = new SolrQuery();

        if (clauses.isEmpty()) {
            query.setQuery("*:*");
        } else {
            query.setQuery(String.join(" AND ", clauses));
        }

        for (String fq : filterQueries) {
            query.addFilterQuery(fq);
        }

        if (!fieldBoosts.isEmpty()) {
            query.set("defType", "edismax");
            String qf = fieldBoosts.entrySet().stream()
                .map(e -> e.getKey() + "^" + e.getValue())
                .collect(Collectors.joining(" "));
            query.set("qf", qf);
        }

        return query;
    }

    private boolean isValidField(String field) {
        // Whitelist of allowed fields
        return ALLOWED_FIELDS.contains(field);
    }

    private static final Set<String> ALLOWED_FIELDS = Set.of(
        "sku", "name", "description", "brand", "category",
        "price", "color", "size", "material", "available"
    );
}

// Good: Type-safe search criteria
public class ProductSearchCriteria {

    private String query;
    private String category;
    private String brand;
    private BigDecimal minPrice;
    private BigDecimal maxPrice;
    private List<String> colors;
    private Boolean inStock;

    // Builders with validation
    public static class Builder {
        private ProductSearchCriteria criteria = new ProductSearchCriteria();

        public Builder query(String query) {
            // Limit query length
            if (query != null && query.length() > 200) {
                query = query.substring(0, 200);
            }
            criteria.query = query;
            return this;
        }

        public Builder category(String category) {
            // Validate category exists
            if (categoryService.exists(category)) {
                criteria.category = category;
            }
            return this;
        }

        public Builder priceRange(BigDecimal min, BigDecimal max) {
            if (min != null && min.compareTo(BigDecimal.ZERO) < 0) {
                min = BigDecimal.ZERO;
            }
            if (max != null && min != null && max.compareTo(min) < 0) {
                max = min;
            }
            criteria.minPrice = min;
            criteria.maxPrice = max;
            return this;
        }

        public ProductSearchCriteria build() {
            return criteria;
        }
    }
}

// Good: Use criteria for type-safe query building
@Injectable
public class ProductSearchService {

    public SearchResult search(ProductSearchCriteria criteria) {
        SearchQueryBuilder builder = new SearchQueryBuilder();

        if (StringUtils.isNotBlank(criteria.getQuery())) {
            builder.term("name", criteria.getQuery())
                   .boost("name", 5f)
                   .boost("sku", 10f)
                   .boost("description", 1f);
        }

        if (StringUtils.isNotBlank(criteria.getCategory())) {
            builder.filter("category", criteria.getCategory());
        }

        if (StringUtils.isNotBlank(criteria.getBrand())) {
            builder.filter("brand", criteria.getBrand());
        }

        if (criteria.getMinPrice() != null || criteria.getMaxPrice() != null) {
            builder.range("price", criteria.getMinPrice(), criteria.getMaxPrice());
        }

        if (criteria.getColors() != null && !criteria.getColors().isEmpty()) {
            for (String color : criteria.getColors()) {
                builder.filter("color", color);
            }
        }

        if (Boolean.TRUE.equals(criteria.getInStock())) {
            builder.filter("available", "true");
        }

        SolrQuery query = builder.build();
        return executeQuery(query);
    }
}

// Good: Query validation and sanitization
@Injectable
public class QuerySanitizer {

    private static final int MAX_QUERY_LENGTH = 500;
    private static final int MAX_TERMS = 20;
    private static final Pattern CONTROL_CHARS = Pattern.compile("[\\x00-\\x1F\\x7F]");

    public String sanitize(String query) {
        if (query == null) {
            return "";
        }

        // Remove control characters
        query = CONTROL_CHARS.matcher(query).replaceAll("");

        // Trim and limit length
        query = query.trim();
        if (query.length() > MAX_QUERY_LENGTH) {
            query = query.substring(0, MAX_QUERY_LENGTH);
        }

        // Limit number of terms
        String[] terms = query.split("\\s+");
        if (terms.length > MAX_TERMS) {
            query = String.join(" ", Arrays.copyOf(terms, MAX_TERMS));
        }

        return query;
    }

    public boolean isValid(String query) {
        if (StringUtils.isBlank(query)) {
            return false;
        }

        // Check for query injection patterns
        if (query.contains("_query_") || query.contains("{!")) {
            return false;
        }

        return true;
    }
}
```

**Query building checklist:**

| Check | Description |
|-------|-------------|
| Escape special chars | Use ClientUtils.escapeQueryChars |
| Validate field names | Whitelist allowed fields |
| Limit query length | Prevent DoS attacks |
| Sanitize input | Remove control characters |
| Use parameterized queries | Prefer filter queries for exact matches |

Reference: [Solr Security](https://solr.apache.org/guide/solr/latest/deployment-guide/security.html)
