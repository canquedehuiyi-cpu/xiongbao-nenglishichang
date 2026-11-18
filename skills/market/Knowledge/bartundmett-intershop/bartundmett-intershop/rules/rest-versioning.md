---
title: Version REST APIs Properly
impact: HIGH
impactDescription: enables backward-compatible API evolution
tags: rest, api, versioning, compatibility
---

## Version REST APIs Properly

**Impact: HIGH (enables backward-compatible API evolution)**

Proper API versioning allows you to evolve APIs without breaking existing clients. Use URL path versioning with clear deprecation policies.

**Incorrect (no versioning strategy):**

```java
// Bad: No versioning - breaking changes affect all clients
@Path("/products")
public class ProductResource {

    @GET
    @Path("/{id}")
    public ProductRO getProduct(@PathParam("id") String id) {
        // If response format changes, all clients break
        return productMapper.toRO(productService.getProduct(id));
    }
}

// Bad: Query parameter versioning - poor cacheability
@GET
@Path("/products/{id}")
public Response getProduct(@PathParam("id") String id,
        @QueryParam("version") String version) {
    // Caching becomes version-dependent
}

// Bad: Header versioning - not visible in URLs
@GET
@Path("/products/{id}")
public Response getProduct(@PathParam("id") String id,
        @HeaderParam("API-Version") String version) {
    // Harder to test, document, and debug
}
```

**Correct (URL path versioning):**

```java
// Good: Clear URL path versioning
@Path("/v1/products")
public class ProductResourceV1 {

    @Inject
    private ProductService productService;

    @GET
    @Path("/{id}")
    @Produces(MediaType.APPLICATION_JSON)
    public ProductRO getProduct(@PathParam("id") String id) {
        ProductBO product = productService.getProduct(id);
        return ProductMapperV1.toRO(product);
    }
}

@Path("/v2/products")
public class ProductResourceV2 {

    @Inject
    private ProductService productService;

    @GET
    @Path("/{id}")
    @Produces(MediaType.APPLICATION_JSON)
    public ProductROV2 getProduct(@PathParam("id") String id) {
        ProductBO product = productService.getProduct(id);
        return ProductMapperV2.toRO(product);  // New response format
    }
}

// Good: Separate Resource Objects per version
public class ProductRO {
    // V1 format
    private String sku;
    private String name;
    private String price;  // String in v1
}

public class ProductROV2 {
    // V2 format with improvements
    private String sku;
    private String name;
    private MoneyRO price;  // Structured money object in v2
    private List<AttributeRO> attributes;  // New field
}

// Good: Shared business logic, version-specific mapping
@Injectable
public class ProductMapperV1 {

    public static ProductRO toRO(ProductBO product) {
        ProductRO ro = new ProductRO();
        ro.setSku(product.getSKU());
        ro.setName(product.getName());
        ro.setPrice(product.getPrice().toString());  // Legacy string format
        return ro;
    }
}

@Injectable
public class ProductMapperV2 {

    public static ProductROV2 toRO(ProductBO product) {
        ProductROV2 ro = new ProductROV2();
        ro.setSku(product.getSKU());
        ro.setName(product.getName());
        ro.setPrice(MoneyMapper.toRO(product.getPrice()));
        ro.setAttributes(mapAttributes(product));
        return ro;
    }
}

// Good: Deprecation headers and documentation
@Path("/v1/products")
@Deprecated
public class ProductResourceV1 {

    @GET
    @Path("/{id}")
    public Response getProduct(@PathParam("id") String id) {
        ProductRO product = // ...

        return Response.ok(product)
            .header("Deprecation", "true")
            .header("Sunset", "Sat, 01 Jul 2026 00:00:00 GMT")
            .header("Link", "</v2/products/" + id + ">; rel=\"successor-version\"")
            .build();
    }
}

// Good: Version negotiation support
@Injectable
public class VersionNegotiationFilter implements ContainerRequestFilter {

    @Override
    public void filter(ContainerRequestContext context) {
        String path = context.getUriInfo().getPath();

        // Redirect unversioned to latest
        if (!path.startsWith("/v")) {
            String latestPath = "/v2" + path;
            context.setRequestUri(URI.create(latestPath));
        }
    }
}

// Good: Backward-compatible field additions (minor version)
public class ProductROV2 {
    private String sku;
    private String name;
    private MoneyRO price;

    // New optional field - backward compatible
    @JsonInclude(JsonInclude.Include.NON_NULL)
    private List<AttributeRO> attributes;

    // Deprecated field - still supported
    @Deprecated
    @JsonProperty("legacyCode")
    private String legacyProductCode;
}

// Good: Version-aware error handling
@Provider
public class VersionedExceptionMapper implements ExceptionMapper<WebApplicationException> {

    @Context
    private UriInfo uriInfo;

    @Override
    public Response toResponse(WebApplicationException exception) {
        int version = extractVersion(uriInfo.getPath());

        if (version == 1) {
            return Response.status(exception.getResponse().getStatus())
                .entity(new ErrorROV1(exception.getMessage()))
                .build();
        } else {
            return Response.status(exception.getResponse().getStatus())
                .entity(new ErrorROV2(
                    exception.getMessage(),
                    generateErrorCode(exception),
                    getTimestamp()
                ))
                .build();
        }
    }
}

// Good: API version lifecycle management
public class APIVersionPolicy {

    public static final Duration DEPRECATION_PERIOD = Duration.ofDays(365);
    public static final Duration SUNSET_NOTICE = Duration.ofDays(90);

    public static final Map<Integer, VersionInfo> VERSIONS = Map.of(
        1, new VersionInfo(
            LocalDate.of(2024, 1, 1),  // Released
            LocalDate.of(2025, 6, 1),  // Deprecated
            LocalDate.of(2026, 6, 1)   // Sunset
        ),
        2, new VersionInfo(
            LocalDate.of(2025, 1, 1),  // Released
            null,                       // Current
            null
        )
    );
}
```

**Version evolution guidelines:**

| Change Type | Impact | Action |
|-------------|--------|--------|
| Add optional field | None | Add to current version |
| Add required field | Breaking | New major version |
| Remove field | Breaking | New major version |
| Change field type | Breaking | New major version |
| Rename field | Breaking | New major version |
| Add endpoint | None | Add to current version |
| Remove endpoint | Breaking | New major version |

Reference: [ICM REST API Guidelines](https://knowledge.intershop.com/kb/index.php/Display/2W2985)
