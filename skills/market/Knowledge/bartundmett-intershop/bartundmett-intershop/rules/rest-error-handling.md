---
title: Use Consistent Error Response Format
impact: HIGH
impactDescription: enables reliable client-side error handling
tags: rest, api, errors, error-handling, consistency
---

## Use Consistent Error Response Format

**Impact: HIGH (enables reliable client-side error handling)**

All API errors must follow a consistent format with proper HTTP status codes, error codes, and actionable messages.

**Incorrect (inconsistent error handling):**

```java
// Bad: Plain string errors
@GET
@Path("/products/{sku}")
public Response getProduct(@PathParam("sku") String sku) {
    ProductBO product = productRepository.getProduct(sku);
    if (product == null) {
        return Response.status(404).entity("Not found").build();
    }
    return Response.ok(product).build();
}

// Bad: Inconsistent error structure
@POST
@Path("/orders")
public Response createOrder(OrderRequest request) {
    try {
        return Response.ok(orderService.create(request)).build();
    } catch (ValidationException e) {
        return Response.status(400)
            .entity(Map.of("error", e.getMessage())).build();
    } catch (Exception e) {
        return Response.status(500)
            .entity(Map.of("msg", "Something went wrong")).build();
    }
}

// Bad: Wrong HTTP status codes
@DELETE
@Path("/products/{sku}")
public Response deleteProduct(@PathParam("sku") String sku) {
    if (!productRepository.exists(sku)) {
        return Response.status(200).entity("Product not found").build();  // Should be 404!
    }
    productRepository.delete(sku);
    return Response.ok().build();
}
```

**Correct (standardized error handling):**

```java
// Good: Standard error response object
public class ErrorRO {
    private String code;           // Machine-readable code
    private String message;        // Human-readable message
    private String target;         // What went wrong (field, resource)
    private List<ErrorDetail> details;  // Additional details
    private String correlationId;  // For support/debugging

    public ErrorRO(String code, String message) {
        this.code = code;
        this.message = message;
        this.correlationId = MDC.get("correlationId");
    }
}

public class ErrorDetail {
    private String code;
    private String message;
    private String target;  // e.g., "quantity" for field errors
}

// Good: Validation error with field details
public class ValidationErrorRO extends ErrorRO {
    private Map<String, List<String>> fieldErrors;

    public ValidationErrorRO(List<FieldError> errors) {
        super("VALIDATION_ERROR", "Request validation failed");
        this.fieldErrors = errors.stream()
            .collect(Collectors.groupingBy(
                FieldError::getField,
                Collectors.mapping(FieldError::getMessage, Collectors.toList())
            ));
    }
}

// Good: Global exception mapper
@Provider
public class GlobalExceptionMapper implements ExceptionMapper<Exception> {

    private static final Logger logger = LoggerFactory.getLogger(GlobalExceptionMapper.class);

    @Override
    public Response toResponse(Exception exception) {

        if (exception instanceof NotFoundException) {
            return Response.status(Response.Status.NOT_FOUND)
                .entity(new ErrorRO("NOT_FOUND", exception.getMessage()))
                .type(MediaType.APPLICATION_JSON)
                .build();
        }

        if (exception instanceof ValidationException) {
            ValidationException ve = (ValidationException) exception;
            return Response.status(Response.Status.BAD_REQUEST)
                .entity(new ValidationErrorRO(ve.getFieldErrors()))
                .type(MediaType.APPLICATION_JSON)
                .build();
        }

        if (exception instanceof ForbiddenException) {
            return Response.status(Response.Status.FORBIDDEN)
                .entity(new ErrorRO("FORBIDDEN", "Access denied"))
                .type(MediaType.APPLICATION_JSON)
                .build();
        }

        if (exception instanceof ConflictException) {
            return Response.status(Response.Status.CONFLICT)
                .entity(new ErrorRO("CONFLICT", exception.getMessage()))
                .type(MediaType.APPLICATION_JSON)
                .build();
        }

        // Log unexpected errors
        logger.error("Unhandled exception", exception);

        // Don't expose internal details
        return Response.status(Response.Status.INTERNAL_SERVER_ERROR)
            .entity(new ErrorRO("INTERNAL_ERROR",
                "An unexpected error occurred. Please try again."))
            .type(MediaType.APPLICATION_JSON)
            .build();
    }
}

// Good: Resource with proper error handling
@Path("/products")
public class ProductResource {

    @GET
    @Path("/{sku}")
    public Response getProduct(@PathParam("sku") String sku) {
        ProductBO product = productRepository.getProduct(sku);

        if (product == null) {
            throw new NotFoundException("Product not found: " + sku);
        }

        return Response.ok(productMapper.toRO(product)).build();
    }

    @POST
    public Response createProduct(@Valid ProductCreateRO request) {
        // @Valid triggers validation, throws ValidationException if invalid

        if (productRepository.existsBySKU(request.getSku())) {
            throw new ConflictException("Product with SKU already exists: " + request.getSku());
        }

        ProductBO product = productService.create(request);

        return Response.created(buildLocation(product))
            .entity(productMapper.toRO(product))
            .build();
    }
}
```

**HTTP status code mapping:**

| Status | Code | Use For |
|--------|------|---------|
| 400 | Bad Request | Validation errors, malformed request |
| 401 | Unauthorized | Missing/invalid authentication |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource, concurrent modification |
| 422 | Unprocessable Entity | Valid syntax but semantic errors |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server errors |
| 503 | Service Unavailable | Temporary downtime |

**Example error responses:**

```json
// 400 Validation Error
{
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "correlationId": "abc123",
  "fieldErrors": {
    "quantity": ["Must be positive", "Maximum is 100"],
    "email": ["Invalid email format"]
  }
}

// 404 Not Found
{
  "code": "NOT_FOUND",
  "message": "Product not found: SKU-123",
  "correlationId": "abc123"
}

// 409 Conflict
{
  "code": "CONCURRENT_MODIFICATION",
  "message": "This order was modified by another user. Please refresh.",
  "correlationId": "abc123"
}
```

Reference: [RFC 7807 - Problem Details for HTTP APIs](https://datatracker.ietf.org/doc/html/rfc7807)
