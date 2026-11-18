---
title: Validate All External Input
impact: CRITICAL
impactDescription: prevents injection attacks and data corruption
tags: security, validation, input, sanitization
---

## Validate All External Input

**Impact: CRITICAL (prevents injection attacks and data corruption)**

All input from external sources (HTTP requests, file uploads, imports) must be validated before processing. Never trust client-side validation alone.

**Incorrect (no server-side validation):**

```java
// Bad: Trusting client input directly
@POST
@Path("/products")
public Response createProduct(ProductCreateRO request) {
    // No validation - accepts anything!
    ProductBO product = productRepository.create(
        request.getSku(),
        request.getName(),
        request.getPrice()
    );
    return Response.ok(product).build();
}

// Bad: Incomplete validation
public void processOrder(String orderId) {
    // Only checks for null, not format
    if (orderId != null) {
        Order order = orderRepository.getOrder(orderId);
        // orderId could be malicious: "1; DROP TABLE orders;--"
    }
}
```

**Correct (comprehensive input validation):**

```java
// Good: Validate at API boundary
@POST
@Path("/products")
public Response createProduct(@Valid ProductCreateRO request) {
    // @Valid triggers JSR-303 validation
    // Additional business validation
    validationService.validateProductCreation(request);

    ProductBO product = productService.createProduct(request);
    return Response.created(buildLocation(product)).entity(product).build();
}

// Good: DTO with validation annotations
public class ProductCreateRO {

    @NotBlank(message = "SKU is required")
    @Size(min = 3, max = 50, message = "SKU must be 3-50 characters")
    @Pattern(regexp = "^[A-Z0-9-]+$", message = "SKU must contain only uppercase letters, numbers, and hyphens")
    private String sku;

    @NotBlank(message = "Name is required")
    @Size(min = 1, max = 255, message = "Name must be 1-255 characters")
    private String name;

    @NotNull(message = "Price is required")
    @DecimalMin(value = "0.01", message = "Price must be positive")
    @DecimalMax(value = "999999.99", message = "Price exceeds maximum")
    private BigDecimal price;

    @Size(max = 5000, message = "Description too long")
    private String description;

    @Email(message = "Invalid email format")
    private String contactEmail;

    // Getters/setters...
}

// Good: Custom validation service for complex rules
@Injectable
public class ProductValidationService {

    @Inject
    private ProductRepository productRepository;

    public void validateProductCreation(ProductCreateRO request) {
        List<ValidationError> errors = new ArrayList<>();

        // Business rule: SKU must be unique
        if (productRepository.existsBySKU(request.getSku())) {
            errors.add(new ValidationError("sku", "SKU already exists"));
        }

        // Business rule: Price must match category constraints
        if (!isPriceValidForCategory(request)) {
            errors.add(new ValidationError("price", "Price not valid for this category"));
        }

        if (!errors.isEmpty()) {
            throw new ValidationException(errors);
        }
    }
}
```

**ID and reference validation:**

```java
// Good: Validate IDs before database lookup
public class OrderService {

    private static final Pattern ORDER_ID_PATTERN = Pattern.compile("^ORD-[A-Z0-9]{8}$");

    public OrderBO getOrder(String orderId) {
        // Validate format before database query
        if (orderId == null || !ORDER_ID_PATTERN.matcher(orderId).matches()) {
            throw new InvalidParameterException("Invalid order ID format");
        }

        OrderBO order = orderRepository.getOrder(orderId);
        if (order == null) {
            throw new NotFoundException("Order not found: " + orderId);
        }

        return order;
    }
}

// Good: Validate numeric ranges
public List<ProductBO> searchProducts(ProductSearchCriteria criteria) {
    // Validate pagination parameters
    int page = Math.max(0, criteria.getPage());
    int pageSize = Math.min(Math.max(1, criteria.getPageSize()), 100);

    // Validate price range
    if (criteria.getMinPrice() != null && criteria.getMaxPrice() != null) {
        if (criteria.getMinPrice().compareTo(criteria.getMaxPrice()) > 0) {
            throw new InvalidParameterException("minPrice cannot exceed maxPrice");
        }
    }

    return productRepository.search(criteria.withPage(page).withPageSize(pageSize));
}
```

**Validation patterns:**

| Input Type | Validation |
|------------|------------|
| IDs | Format pattern, existence check |
| Strings | Length, allowed characters, sanitize HTML |
| Numbers | Range, precision, sign |
| Dates | Format, valid range, not in past/future |
| Emails | Format, domain validation |
| URLs | Format, allowed protocols, domain whitelist |
| Files | Size, type, content validation |

Reference: [JSR-303 Bean Validation](https://beanvalidation.org/)
