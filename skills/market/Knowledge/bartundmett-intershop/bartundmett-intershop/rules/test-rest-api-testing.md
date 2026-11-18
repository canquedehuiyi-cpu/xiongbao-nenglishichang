---
title: Test REST APIs with Integration Tests
impact: HIGH
impactDescription: validates API contracts and error handling
tags: testing, rest, api, integration, http
---

## Test REST APIs with Integration Tests

**Impact: HIGH (validates API contracts and error handling)**

REST resources should have integration tests that validate HTTP status codes, response formats, authentication, and error handling.

**Incorrect (only testing resource methods directly):**

```java
// Bad: Only tests Java method, not HTTP layer
@Test
public void testGetProduct() {
    ProductResource resource = new ProductResource();
    Response response = resource.getProduct("SKU123");

    assertEquals(200, response.getStatus());
    // Misses: headers, content-type, serialization, auth
}
```

**Correct (full HTTP integration test):**

```java
// Good: Tests complete HTTP request/response cycle
public class ProductResourceIT extends AbstractRestIntegrationTest {

    @Test
    public void getProduct_existingProduct_returns200WithProductData() {
        // Arrange - ensure product exists
        createTestProduct("SKU123", "Test Product", 99.99);

        // Act - make HTTP request
        Response response = target("/products/SKU123")
            .request(MediaType.APPLICATION_JSON)
            .header("Authorization", "Bearer " + getValidToken())
            .get();

        // Assert - verify HTTP response
        assertEquals(Response.Status.OK.getStatusCode(), response.getStatus());
        assertEquals("application/json", response.getMediaType().toString());

        // Assert - verify response body
        ProductRO product = response.readEntity(ProductRO.class);
        assertEquals("SKU123", product.getSku());
        assertEquals("Test Product", product.getName());
        assertEquals(99.99, product.getPrice().getValue().doubleValue(), 0.01);

        // Assert - verify HATEOAS links
        assertNotNull(product.getLinks());
        assertTrue(product.getLinks().stream()
            .anyMatch(link -> "self".equals(link.getRel())));
    }

    @Test
    public void getProduct_nonExistentProduct_returns404WithErrorBody() {
        Response response = target("/products/NONEXISTENT")
            .request(MediaType.APPLICATION_JSON)
            .header("Authorization", "Bearer " + getValidToken())
            .get();

        assertEquals(Response.Status.NOT_FOUND.getStatusCode(), response.getStatus());

        ErrorRO error = response.readEntity(ErrorRO.class);
        assertEquals("PRODUCT_NOT_FOUND", error.getCode());
        assertNotNull(error.getMessage());
    }

    @Test
    public void getProduct_noAuthentication_returns401() {
        Response response = target("/products/SKU123")
            .request(MediaType.APPLICATION_JSON)
            // No Authorization header
            .get();

        assertEquals(Response.Status.UNAUTHORIZED.getStatusCode(), response.getStatus());
    }

    @Test
    public void getProduct_invalidToken_returns401() {
        Response response = target("/products/SKU123")
            .request(MediaType.APPLICATION_JSON)
            .header("Authorization", "Bearer invalid-token")
            .get();

        assertEquals(Response.Status.UNAUTHORIZED.getStatusCode(), response.getStatus());
    }

    @Test
    public void createProduct_validData_returns201WithLocation() {
        ProductCreateRO createRequest = new ProductCreateRO();
        createRequest.setSku("NEW-SKU");
        createRequest.setName("New Product");
        createRequest.setPrice(49.99);

        Response response = target("/products")
            .request(MediaType.APPLICATION_JSON)
            .header("Authorization", "Bearer " + getAdminToken())
            .post(Entity.json(createRequest));

        assertEquals(Response.Status.CREATED.getStatusCode(), response.getStatus());

        // Verify Location header
        String location = response.getHeaderString("Location");
        assertNotNull(location);
        assertTrue(location.endsWith("/products/NEW-SKU"));

        // Verify response body
        ProductRO created = response.readEntity(ProductRO.class);
        assertEquals("NEW-SKU", created.getSku());
    }

    @Test
    public void createProduct_invalidData_returns400WithValidationErrors() {
        ProductCreateRO invalidRequest = new ProductCreateRO();
        // Missing required fields: sku, name

        Response response = target("/products")
            .request(MediaType.APPLICATION_JSON)
            .header("Authorization", "Bearer " + getAdminToken())
            .post(Entity.json(invalidRequest));

        assertEquals(Response.Status.BAD_REQUEST.getStatusCode(), response.getStatus());

        ValidationErrorRO error = response.readEntity(ValidationErrorRO.class);
        assertTrue(error.getFieldErrors().containsKey("sku"));
        assertTrue(error.getFieldErrors().containsKey("name"));
    }

    @Test
    public void createProduct_unauthorizedUser_returns403() {
        ProductCreateRO request = new ProductCreateRO();
        request.setSku("NEW-SKU");
        request.setName("New Product");

        Response response = target("/products")
            .request(MediaType.APPLICATION_JSON)
            .header("Authorization", "Bearer " + getReadOnlyUserToken())
            .post(Entity.json(request));

        assertEquals(Response.Status.FORBIDDEN.getStatusCode(), response.getStatus());
    }
}
```

**Test coverage matrix:**

| Scenario | Expected Status | Verify |
|----------|-----------------|--------|
| Valid request | 200/201 | Body, headers, links |
| Not found | 404 | Error body |
| No auth | 401 | Error body |
| Bad auth | 401 | Error body |
| No permission | 403 | Error body |
| Invalid input | 400 | Validation errors |
| Server error | 500 | Error body |

**Testing pagination:**

```java
@Test
public void listProducts_withPagination_returnsCorrectPage() {
    // Create 25 test products
    createTestProducts(25);

    Response response = target("/products")
        .queryParam("page", 1)
        .queryParam("pageSize", 10)
        .request(MediaType.APPLICATION_JSON)
        .header("Authorization", "Bearer " + getValidToken())
        .get();

    ProductCollectionRO collection = response.readEntity(ProductCollectionRO.class);

    assertEquals(10, collection.getElements().size());
    assertEquals(25, collection.getTotal());
    assertEquals(1, collection.getPage());
    assertEquals(3, collection.getTotalPages());
}
```

Reference: [Guide - REST Style Guide](https://knowledge.intershop.com/kb/index.php/Display/25127U)
