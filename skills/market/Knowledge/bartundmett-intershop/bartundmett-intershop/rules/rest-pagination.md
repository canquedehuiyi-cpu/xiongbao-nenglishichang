---
title: Implement Proper Pagination for Collections
impact: HIGH
impactDescription: prevents memory issues and improves API performance
tags: rest, api, pagination, performance, collections
---

## Implement Proper Pagination for Collections

**Impact: HIGH (prevents memory issues and improves API performance)**

All collection endpoints must support pagination to handle large datasets efficiently and provide consistent client experience.

**Incorrect (no pagination):**

```java
// Bad: Returns all results - memory issues, slow response
@GET
@Path("/products")
public List<ProductRO> getAllProducts() {
    List<ProductBO> products = productRepository.findAll();  // Could be 100,000+!
    return productMapper.toRO(products);
}

// Bad: Inconsistent pagination parameters
@GET
@Path("/orders")
public List<OrderRO> getOrders(
    @QueryParam("start") Integer start,
    @QueryParam("count") Integer count) { }

@GET
@Path("/customers")
public List<CustomerRO> getCustomers(
    @QueryParam("offset") Integer offset,
    @QueryParam("limit") Integer limit) { }
```

**Correct (standardized pagination):**

```java
// Good: Standard pagination response wrapper
public class PagedResult<T> {
    private List<T> elements;
    private int page;
    private int pageSize;
    private long total;
    private int totalPages;
    private Links links;

    public static class Links {
        private String self;
        private String first;
        private String prev;
        private String next;
        private String last;
    }
}

// Good: Paginated endpoint with consistent parameters
@GET
@Path("/products")
@Produces(MediaType.APPLICATION_JSON)
public Response getProducts(
        @QueryParam("page") @DefaultValue("0") int page,
        @QueryParam("pageSize") @DefaultValue("20") int pageSize,
        @QueryParam("sort") @DefaultValue("name") String sort,
        @QueryParam("direction") @DefaultValue("asc") String direction,
        @Context UriInfo uriInfo) {

    // Validate and constrain parameters
    page = Math.max(0, page);
    pageSize = Math.min(Math.max(1, pageSize), 100);  // Max 100 per page

    // Fetch data
    PagedResult<ProductBO> result = productRepository.findAll(
        PageRequest.of(page, pageSize, Sort.by(direction, sort)));

    // Build response with HATEOAS links
    PagedResult<ProductRO> response = new PagedResult<>();
    response.setElements(productMapper.toRO(result.getContent()));
    response.setPage(page);
    response.setPageSize(pageSize);
    response.setTotal(result.getTotalElements());
    response.setTotalPages(result.getTotalPages());
    response.setLinks(buildLinks(uriInfo, page, pageSize, result.getTotalPages()));

    return Response.ok(response).build();
}

private Links buildLinks(UriInfo uriInfo, int page, int pageSize, int totalPages) {
    Links links = new Links();
    UriBuilder builder = uriInfo.getAbsolutePathBuilder();

    links.setSelf(builder.replaceQueryParam("page", page)
        .replaceQueryParam("pageSize", pageSize).build().toString());

    links.setFirst(builder.replaceQueryParam("page", 0).build().toString());

    if (page > 0) {
        links.setPrev(builder.replaceQueryParam("page", page - 1).build().toString());
    }

    if (page < totalPages - 1) {
        links.setNext(builder.replaceQueryParam("page", page + 1).build().toString());
    }

    links.setLast(builder.replaceQueryParam("page", totalPages - 1).build().toString());

    return links;
}
```

**Cursor-based pagination for large/real-time data:**

```java
// Good: Cursor pagination for scalability
@GET
@Path("/events")
public Response getEvents(
        @QueryParam("cursor") String cursor,
        @QueryParam("limit") @DefaultValue("50") int limit) {

    limit = Math.min(limit, 100);

    CursorPagedResult<EventBO> result;
    if (cursor != null) {
        result = eventRepository.findAfterCursor(decodeCursor(cursor), limit);
    } else {
        result = eventRepository.findFirst(limit);
    }

    CursorPagedResult<EventRO> response = new CursorPagedResult<>();
    response.setElements(eventMapper.toRO(result.getElements()));
    response.setNextCursor(encodeCursor(result.getLastElement()));
    response.setHasMore(result.hasMore());

    return Response.ok(response).build();
}

// Cursor encodes position for efficient keyset pagination
private String encodeCursor(EventBO event) {
    // e.g., Base64 encoded: "timestamp:id"
    return Base64.encode(event.getTimestamp() + ":" + event.getId());
}
```

**Repository implementation:**

```java
// Good: Efficient pagination query
public class ProductRepositoryImpl implements ProductRepository {

    @Override
    public PagedResult<ProductBO> findAll(PageRequest pageRequest) {
        // Count query (can be cached)
        long total = countProducts();

        // Data query with limit/offset
        String hql = "FROM ProductPO p ORDER BY p." + pageRequest.getSortField();
        Query query = queryManager.createQuery(hql);
        query.setFirstResult(pageRequest.getOffset());
        query.setMaxResults(pageRequest.getPageSize());

        List<ProductBO> products = query.list().stream()
            .map(ProductBOImpl::new)
            .collect(Collectors.toList());

        return new PagedResult<>(products, pageRequest, total);
    }

    // Cursor-based for better performance on large datasets
    @Override
    public CursorPagedResult<ProductBO> findAfterCursor(String lastId, int limit) {
        String hql = "FROM ProductPO p WHERE p.id > :lastId ORDER BY p.id";
        Query query = queryManager.createQuery(hql);
        query.setParameter("lastId", lastId);
        query.setMaxResults(limit + 1);  // Fetch one extra to detect hasMore

        List<ProductPO> results = query.list();
        boolean hasMore = results.size() > limit;

        if (hasMore) {
            results = results.subList(0, limit);
        }

        return new CursorPagedResult<>(
            results.stream().map(ProductBOImpl::new).collect(Collectors.toList()),
            hasMore
        );
    }
}
```

**Pagination comparison:**

| Method | Pros | Cons | Use When |
|--------|------|------|----------|
| Offset | Simple, random access | Slow for large offsets | < 10k items |
| Cursor | Fast, consistent | No random access | Large datasets, real-time |
| Keyset | Very fast | Complex implementation | Sorted data, high volume |

Reference: [REST API Pagination Best Practices](https://www.moesif.com/blog/technical/api-design/REST-API-Design-Filtering-Sorting-and-Pagination/)
