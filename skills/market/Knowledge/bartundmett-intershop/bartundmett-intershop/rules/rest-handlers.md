---
title: Use Handlers for Customizable REST Resources
impact: HIGH
impactDescription: enables flexible API customization without modifying core resources
tags: rest, handlers, customization, extension
---

## Use Handlers for Customizable REST Resources

**Impact: HIGH (enables flexible API customization without modifying core resources)**

REST resource handlers allow separating API endpoint logic from business object access. This enables customization of data retrieval without modifying the resource class itself.

**Incorrect (direct business logic in resource):**

```java
// Bad: All logic hardcoded in resource - hard to customize
@Path("/products")
public class ProductResource extends AbstractRestResource {

    @Inject
    private ProductRepository productRepository;

    @GET
    @Path("/{sku}")
    public Response getProduct(@PathParam("sku") String sku) {
        // Direct repository access - can't customize without modifying this class
        ProductBO product = productRepository.getProduct(sku);

        // Business logic embedded in resource
        if (product == null) {
            return Response.status(404).build();
        }

        if (!product.isVisible()) {
            return Response.status(403).build();
        }

        // Can't change how product is fetched or enriched
        return Response.ok(mapper.toRO(product)).build();
    }
}
```

**Correct (using handler pattern):**

```java
// 1. Define handler interface
public interface ProductResourceHandler {

    /**
     * Retrieves a product for the REST response.
     * Can be overridden to customize data retrieval and enrichment.
     */
    ProductBO getProduct(String sku, ProductResourceContext context);

    /**
     * Checks if the product should be visible to the current user.
     */
    boolean isProductVisible(ProductBO product, ProductResourceContext context);

    /**
     * Enriches the product with additional data before response.
     */
    void enrichProduct(ProductBO product, ProductResourceContext context);
}

// 2. Default handler implementation
public class DefaultProductResourceHandler implements ProductResourceHandler {

    @Inject
    private ProductRepository productRepository;

    @Override
    public ProductBO getProduct(String sku, ProductResourceContext context) {
        return productRepository.getProduct(sku);
    }

    @Override
    public boolean isProductVisible(ProductBO product, ProductResourceContext context) {
        return product != null && product.isVisible();
    }

    @Override
    public void enrichProduct(ProductBO product, ProductResourceContext context) {
        // Default: no enrichment
    }
}

// 3. REST resource uses handler
@Path("/products")
public class ProductResource extends AbstractRestResource {

    @Inject
    private ProductResourceHandler handler;  // Injected, can be overridden

    @Inject
    private ProductROMapper mapper;

    @GET
    @Path("/{sku}")
    public Response getProduct(@PathParam("sku") String sku) {
        ProductResourceContext context = createContext();

        // Delegate to handler for customizable retrieval
        ProductBO product = handler.getProduct(sku, context);

        if (!handler.isProductVisible(product, context)) {
            return Response.status(Response.Status.NOT_FOUND).build();
        }

        // Allow handler to enrich data
        handler.enrichProduct(product, context);

        return Response.ok(mapper.toRO(product)).build();
    }
}

// 4. Custom handler for specific project requirements
public class B2BProductResourceHandler extends DefaultProductResourceHandler {

    @Inject
    private CustomerPriceService customerPriceService;

    @Inject
    private ContractService contractService;

    @Override
    public ProductBO getProduct(String sku, ProductResourceContext context) {
        ProductBO product = super.getProduct(sku, context);

        // B2B-specific: apply customer contract
        if (context.hasActiveContract()) {
            contractService.applyContractTerms(product, context.getContract());
        }

        return product;
    }

    @Override
    public void enrichProduct(ProductBO product, ProductResourceContext context) {
        // Add customer-specific pricing
        Money customerPrice = customerPriceService.getPrice(
            product,
            context.getCustomer()
        );
        context.setAttribute("customerPrice", customerPrice);
    }
}

// 5. Override binding via Guice
public class B2BProductModule extends AbstractModule {
    @Override
    protected void configure() {
        bind(ProductResourceHandler.class)
            .to(B2BProductResourceHandler.class);
    }
}
```

**Handler design patterns:**

| Pattern | Use Case |
|---------|----------|
| Default + Override | Base functionality with customization points |
| Chain of Responsibility | Multiple handlers in sequence |
| Strategy | Completely different implementations per context |
| Decorator | Add behavior without modifying original |

**Context object for passing request-scoped data:**

```java
public class ProductResourceContext {
    private final UserBO currentUser;
    private final CustomerBO customer;
    private final ContractBO contract;
    private final Map<String, Object> attributes = new HashMap<>();

    // Rich context enables flexible handler implementations
    public boolean hasActiveContract() {
        return contract != null && contract.isActive();
    }
}
```

Reference: [Concept - REST Framework](https://knowledge.intershop.com/kb/index.php/Display/2324R8)
