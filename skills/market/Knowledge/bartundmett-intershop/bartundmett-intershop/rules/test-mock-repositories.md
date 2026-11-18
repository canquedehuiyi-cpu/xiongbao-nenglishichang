---
title: Mock Repositories Properly for Isolated Tests
impact: HIGH
impactDescription: enables fast, deterministic tests without database
tags: testing, mocking, repositories, isolation
---

## Mock Repositories Properly for Isolated Tests

**Impact: HIGH (enables fast, deterministic tests without database)**

Repository interfaces should be mocked in unit tests to avoid database dependencies. Create reusable mock setups for common scenarios.

**Incorrect (using real repository or incomplete mocking):**

```java
// Bad: Incomplete mocking - will fail unexpectedly
@Test
public void testGetProductDetails() {
    ProductRepository repo = mock(ProductRepository.class);
    ProductBO product = mock(ProductBO.class);

    when(repo.getProduct("SKU123")).thenReturn(product);
    // Missing: product.getSKU(), product.getName(), etc.

    ProductService service = new ProductService(repo);
    ProductDetails details = service.getDetails("SKU123");

    // NullPointerException when accessing product properties!
}
```

**Correct (comprehensive mock setup):**

```java
// Good: Complete mock setup with builder
public class ProductRepositoryMockBuilder {

    private final ProductRepository mockRepo = mock(ProductRepository.class);
    private final Map<String, ProductBO> products = new HashMap<>();

    public ProductRepositoryMockBuilder withProduct(ProductBO product) {
        products.put(product.getSKU(), product);
        when(mockRepo.getProduct(product.getSKU())).thenReturn(product);
        return this;
    }

    public ProductRepositoryMockBuilder withProducts(List<ProductBO> productList) {
        productList.forEach(this::withProduct);
        when(mockRepo.getAllProducts()).thenReturn(new ArrayList<>(products.values()));
        return this;
    }

    public ProductRepositoryMockBuilder withNoProduct(String sku) {
        when(mockRepo.getProduct(sku)).thenReturn(null);
        return this;
    }

    public ProductRepositoryMockBuilder withSearchResult(String query, List<ProductBO> results) {
        when(mockRepo.search(argThat(criteria ->
            criteria.getQuery().contains(query)))).thenReturn(results);
        return this;
    }

    public ProductRepository build() {
        return mockRepo;
    }
}

// Usage in tests
public class ProductServiceTest {

    @Test
    public void testGetDetails_existingProduct_returnsFullDetails() {
        // Arrange - use builder for complete mock
        ProductBO product = TestProductBuilder.aProduct()
            .withSKU("SKU123")
            .withName("Test Product")
            .withPrice(Money.of(99.99, "EUR"))
            .withCategory("Electronics")
            .build();

        ProductRepository repo = new ProductRepositoryMockBuilder()
            .withProduct(product)
            .build();

        ProductService service = new ProductService(repo);

        // Act
        ProductDetails details = service.getDetails("SKU123");

        // Assert
        assertEquals("Test Product", details.getName());
        assertEquals(Money.of(99.99, "EUR"), details.getPrice());
    }

    @Test
    public void testGetDetails_nonExistentProduct_throwsNotFoundException() {
        ProductRepository repo = new ProductRepositoryMockBuilder()
            .withNoProduct("UNKNOWN")
            .build();

        ProductService service = new ProductService(repo);

        assertThrows(ProductNotFoundException.class, () -> {
            service.getDetails("UNKNOWN");
        });
    }
}
```

**Test data builder for business objects:**

```java
public class TestProductBuilder {

    private String sku = "DEFAULT-SKU";
    private String name = "Default Product";
    private Money price = Money.of(10, "EUR");
    private boolean available = true;
    private CategoryBO category;

    public static TestProductBuilder aProduct() {
        return new TestProductBuilder();
    }

    public TestProductBuilder withSKU(String sku) {
        this.sku = sku;
        return this;
    }

    public TestProductBuilder withName(String name) {
        this.name = name;
        return this;
    }

    public TestProductBuilder withPrice(Money price) {
        this.price = price;
        return this;
    }

    public TestProductBuilder unavailable() {
        this.available = false;
        return this;
    }

    public ProductBO build() {
        ProductBO product = mock(ProductBO.class);
        when(product.getSKU()).thenReturn(sku);
        when(product.getName()).thenReturn(name);
        when(product.getPrice()).thenReturn(price);
        when(product.isAvailable()).thenReturn(available);
        when(product.getCategory()).thenReturn(category);
        return product;
    }
}
```

**Mocking patterns:**

| Pattern | Use Case |
|---------|----------|
| Builder | Complex objects with many properties |
| Factory method | Simple, common test objects |
| Argument matcher | Flexible matching for queries |
| Answer | Dynamic responses based on input |

Reference: [Mockito Documentation](https://site.mockito.org/)
