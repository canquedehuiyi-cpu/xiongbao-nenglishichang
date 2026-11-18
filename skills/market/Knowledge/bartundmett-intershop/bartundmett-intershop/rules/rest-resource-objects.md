---
title: Use Proper Resource Object Patterns
impact: HIGH
impactDescription: ensures consistent API responses and proper serialization
tags: rest, api, resource-objects, serialization, json
---

## Use Proper Resource Object Patterns

**Impact: HIGH (ensures consistent API responses and proper serialization)**

Resource Objects (ROs) define the JSON structure of REST API responses. Proper design ensures consistency, extensibility, and clean separation from internal business objects.

**Incorrect (exposing internal objects):**

```java
// Bad: Returning internal BO directly
@Path("/products")
public class ProductResource {

    @GET
    @Path("/{sku}")
    public ProductBO getProduct(@PathParam("sku") String sku) {
        // Exposes internal implementation!
        // May serialize fields you don't want public
        // Tight coupling to internal structure
        return productRepository.getProduct(sku);
    }
}

// Bad: Inline JSON construction
@GET
@Path("/{sku}")
public Response getProduct(@PathParam("sku") String sku) {
    ProductBO product = productRepository.getProduct(sku);
    // Fragile, inconsistent JSON structure
    return Response.ok("{\"sku\":\"" + product.getSKU() + "\"}").build();
}
```

**Correct (using Resource Objects):**

```java
// 1. Define Resource Object extending AbstractResourceObject
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ProductRO extends AbstractResourceObject {

    @JsonProperty("sku")
    private String sku;

    @JsonProperty("name")
    private String name;

    @JsonProperty("description")
    private String description;

    @JsonProperty("price")
    private MoneyRO price;

    @JsonProperty("availability")
    private AvailabilityRO availability;

    @JsonProperty("attributes")
    private Map<String, Object> attributes;

    // Links for HATEOAS
    @JsonProperty("links")
    private List<LinkRO> links;

    // Getters and setters...

    // Builder pattern for clean construction
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private final ProductRO ro = new ProductRO();

        public Builder sku(String sku) {
            ro.sku = sku;
            return this;
        }

        public Builder name(String name) {
            ro.name = name;
            return this;
        }

        public Builder fromBO(ProductBO product) {
            ro.sku = product.getSKU();
            ro.name = product.getName();
            ro.description = product.getDescription();
            return this;
        }

        public ProductRO build() {
            return ro;
        }
    }
}

// 2. Create mapper for BO to RO conversion
@Injectable
public class ProductROMapper {

    @Inject
    private MoneyROMapper moneyMapper;

    @Inject
    private AvailabilityROMapper availabilityMapper;

    @Inject
    private LinkBuilder linkBuilder;

    public ProductRO toRO(ProductBO product) {
        return ProductRO.builder()
            .sku(product.getSKU())
            .name(product.getName())
            .description(product.getDescription())
            .price(moneyMapper.toRO(product.getPrice()))
            .availability(availabilityMapper.toRO(product.getAvailability()))
            .links(buildLinks(product))
            .build();
    }

    public List<ProductRO> toRO(List<ProductBO> products) {
        return products.stream()
            .map(this::toRO)
            .collect(Collectors.toList());
    }

    private List<LinkRO> buildLinks(ProductBO product) {
        return Arrays.asList(
            linkBuilder.buildSelfLink(product),
            linkBuilder.buildLink("images", "/products/" + product.getSKU() + "/images"),
            linkBuilder.buildLink("reviews", "/products/" + product.getSKU() + "/reviews")
        );
    }
}

// 3. Use in REST resource
@Path("/products")
public class ProductResource extends AbstractRestResource {

    @Inject
    private ProductRepository productRepository;

    @Inject
    private ProductROMapper productMapper;

    @GET
    @Path("/{sku}")
    @Produces(MediaType.APPLICATION_JSON)
    public Response getProduct(@PathParam("sku") String sku) {
        ProductBO product = productRepository.getProduct(sku);

        if (product == null) {
            return Response.status(Response.Status.NOT_FOUND)
                .entity(new ErrorRO("Product not found", "PRODUCT_NOT_FOUND"))
                .build();
        }

        ProductRO productRO = productMapper.toRO(product);

        return Response.ok(productRO).build();
    }

    @GET
    @Produces(MediaType.APPLICATION_JSON)
    public Response listProducts(@QueryParam("category") String category) {
        List<ProductBO> products = productRepository.findByCategory(category);
        List<ProductRO> productROs = productMapper.toRO(products);

        // Collection response with metadata
        ProductCollectionRO collection = new ProductCollectionRO();
        collection.setElements(productROs);
        collection.setTotal(products.size());

        return Response.ok(collection).build();
    }
}
```

**Resource Object design guidelines:**

| Guideline | Description |
|-----------|-------------|
| Use @JsonProperty | Explicit field naming |
| NON_NULL inclusion | Don't serialize null fields |
| Builder pattern | Clean construction |
| Separate RO and BO | Never expose internal objects |
| HATEOAS links | Self-documenting API |
| Error ROs | Consistent error format |

Reference: [Concept - REST Framework](https://knowledge.intershop.com/kb/index.php/Display/2324R8)
