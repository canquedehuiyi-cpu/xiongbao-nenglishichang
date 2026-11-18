---
title: Implement HATEOAS Links Properly
impact: MEDIUM
impactDescription: improves API discoverability and client flexibility
tags: rest, hateoas, links, hypermedia
---

## Implement HATEOAS Links Properly

**Impact: MEDIUM (improves API discoverability and client flexibility)**

HATEOAS (Hypermedia as the Engine of Application State) enables self-documenting APIs where clients discover available actions through links rather than hardcoding URLs.

**Incorrect (no hypermedia links):**

```java
// Bad: No links - clients must construct URLs
@GET
@Path("/{id}")
public ProductRO getProduct(@PathParam("id") String id) {
    ProductBO product = productService.getProduct(id);
    ProductRO ro = new ProductRO();
    ro.setSku(product.getSKU());
    ro.setName(product.getName());
    return ro;  // No navigation links
}

// Bad: Hardcoded URLs in clients
// Client code:
// String updateUrl = baseUrl + "/products/" + product.id;  // Fragile!

// Bad: Inconsistent link format
public class ProductRO {
    private String sku;
    private String updateLink;  // Just a string
    private Map<String, String> actions;  // Unstructured
}
```

**Correct (proper HATEOAS implementation):**

```java
// Good: Standard link structure
public class LinkRO {
    private String href;
    private String rel;
    private String type;
    private String method;
    private String title;

    public static LinkRO of(String href, String rel) {
        LinkRO link = new LinkRO();
        link.setHref(href);
        link.setRel(rel);
        return link;
    }

    public static LinkRO self(String href) {
        return of(href, "self");
    }
}

// Good: Resource with embedded links
public class ProductRO extends AbstractResourceObject {
    private String sku;
    private String name;
    private MoneyRO price;
    private List<LinkRO> links;

    @JsonProperty("_links")
    public Map<String, LinkRO> getLinksMap() {
        return links.stream()
            .collect(Collectors.toMap(LinkRO::getRel, l -> l));
    }
}

// Good: Link builder for consistent URL generation
@Injectable
public class LinkBuilder {

    @Context
    private UriInfo uriInfo;

    public LinkRO buildProductLink(String productId, String rel) {
        String href = uriInfo.getBaseUriBuilder()
            .path(ProductResource.class)
            .path(productId)
            .build()
            .toString();

        return LinkRO.of(href, rel);
    }

    public LinkRO buildCollectionLink(Class<?> resourceClass, String rel,
            Map<String, Object> queryParams) {
        UriBuilder builder = uriInfo.getBaseUriBuilder()
            .path(resourceClass);

        queryParams.forEach((k, v) -> builder.queryParam(k, v));

        return LinkRO.of(builder.build().toString(), rel);
    }
}

// Good: Resource with contextual links
@Injectable
public class ProductResourceMapper {

    @Inject
    private LinkBuilder linkBuilder;

    @Inject
    private AuthorizationService authService;

    public ProductRO toRO(ProductBO product, UserBO currentUser) {
        ProductRO ro = new ProductRO();
        ro.setSku(product.getSKU());
        ro.setName(product.getName());
        ro.setPrice(MoneyMapper.toRO(product.getPrice()));

        List<LinkRO> links = new ArrayList<>();

        // Self link - always present
        links.add(linkBuilder.buildProductLink(product.getId(), "self"));

        // Collection link
        links.add(linkBuilder.buildCollectionLink(
            ProductResource.class, "collection", Map.of()));

        // Conditional links based on permissions
        if (authService.canEdit(currentUser, product)) {
            LinkRO editLink = linkBuilder.buildProductLink(product.getId(), "edit");
            editLink.setMethod("PUT");
            links.add(editLink);
        }

        if (authService.canDelete(currentUser, product)) {
            LinkRO deleteLink = linkBuilder.buildProductLink(product.getId(), "delete");
            deleteLink.setMethod("DELETE");
            links.add(deleteLink);
        }

        // Related resources
        links.add(LinkRO.of(
            buildCategoryUrl(product.getCategory()),
            "category"
        ));

        links.add(LinkRO.of(
            buildPricesUrl(product.getId()),
            "prices"
        ));

        if (product.hasVariants()) {
            links.add(LinkRO.of(
                buildVariantsUrl(product.getId()),
                "variants"
            ));
        }

        ro.setLinks(links);
        return ro;
    }
}

// Good: Collection with pagination links
@Injectable
public class ProductCollectionMapper {

    public ProductCollectionRO toRO(Page<ProductBO> page, UriInfo uriInfo) {
        ProductCollectionRO ro = new ProductCollectionRO();
        ro.setItems(page.getContent().stream()
            .map(this::toItemRO)
            .collect(toList()));

        // Pagination metadata
        ro.setPage(page.getNumber());
        ro.setPageSize(page.getSize());
        ro.setTotalElements(page.getTotalElements());
        ro.setTotalPages(page.getTotalPages());

        // Pagination links
        List<LinkRO> links = new ArrayList<>();

        // Self
        links.add(buildPageLink(uriInfo, page.getNumber(), "self"));

        // First
        links.add(buildPageLink(uriInfo, 0, "first"));

        // Last
        links.add(buildPageLink(uriInfo, page.getTotalPages() - 1, "last"));

        // Previous
        if (page.hasPrevious()) {
            links.add(buildPageLink(uriInfo, page.getNumber() - 1, "prev"));
        }

        // Next
        if (page.hasNext()) {
            links.add(buildPageLink(uriInfo, page.getNumber() + 1, "next"));
        }

        ro.setLinks(links);
        return ro;
    }

    private LinkRO buildPageLink(UriInfo uriInfo, int page, String rel) {
        String href = uriInfo.getRequestUriBuilder()
            .replaceQueryParam("page", page)
            .build()
            .toString();

        return LinkRO.of(href, rel);
    }
}

// Good: Action links with templates
public class OrderRO extends AbstractResourceObject {
    private String orderId;
    private String status;
    private List<LinkRO> links;

    // For orders, include available actions
    @JsonProperty("_actions")
    public List<ActionRO> getActions() {
        List<ActionRO> actions = new ArrayList<>();

        if ("PENDING".equals(status)) {
            actions.add(ActionRO.builder()
                .name("approve")
                .href(links.stream()
                    .filter(l -> "approve".equals(l.getRel()))
                    .findFirst()
                    .map(LinkRO::getHref)
                    .orElse(null))
                .method("POST")
                .build());

            actions.add(ActionRO.builder()
                .name("reject")
                .href(links.stream()
                    .filter(l -> "reject".equals(l.getRel()))
                    .findFirst()
                    .map(LinkRO::getHref)
                    .orElse(null))
                .method("POST")
                .fields(List.of(
                    new FieldRO("reason", "string", true)
                ))
                .build());
        }

        return actions;
    }
}
```

**Standard link relations:**

| Rel | Description |
|-----|-------------|
| self | Current resource URL |
| collection | Parent collection |
| first, last, prev, next | Pagination |
| edit | URL for PUT/PATCH |
| delete | URL for DELETE |
| related | Associated resources |
| search | Search endpoint |

Reference: [IANA Link Relations](https://www.iana.org/assignments/link-relations/)
