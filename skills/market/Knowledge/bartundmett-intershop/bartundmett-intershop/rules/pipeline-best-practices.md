---
title: Follow Pipeline Design Best Practices
impact: MEDIUM
impactDescription: ensures maintainable and testable business workflows
tags: pipeline, pipelet, workflow, best-practices
---

## Follow Pipeline Design Best Practices

**Impact: MEDIUM (ensures maintainable and testable business workflows)**

Pipelines model business workflows by connecting pipelets. Following design best practices ensures maintainable, reusable, and testable workflows.

**Incorrect (monolithic pipeline with complex logic):**

```xml
<!-- Bad: Overly complex viewing pipeline with too much logic -->
<pipeline name="ViewProduct" type="view">
    <node name="Start">
        <!-- Doing everything in one place -->
        <pipelet name="GetProduct"/>
        <pipelet name="CalculatePrice"/>
        <pipelet name="CheckAvailability"/>
        <pipelet name="GetRelatedProducts"/>
        <pipelet name="GetReviews"/>
        <pipelet name="TrackAnalytics"/>
        <pipelet name="RenderTemplate"/>
    </node>
</pipeline>

<!-- Bad: Pipelet with too much responsibility -->
public class DoEverythingPipelet extends Pipelet {
    @Override
    public int execute(PipelineDictionary dict) {
        // 200 lines of mixed concerns
        // Impossible to test, reuse, or maintain
    }
}
```

**Correct (separated viewing and process pipelines):**

```xml
<!-- 1. Viewing Pipeline - handles page flow only -->
<pipeline name="ViewProduct" type="view">
    <node name="Start">
        <pipelet name="ValidateProductID"/>
        <transition condition="valid" to="GetProductDetails"/>
        <transition condition="invalid" to="ShowError"/>
    </node>

    <node name="GetProductDetails">
        <!-- Call process pipeline for business logic -->
        <call-pipeline name="GetProductData"
                       pipe="process/ProductProcess">
            <param name="ProductID" from="ProductID"/>
        </call-pipeline>
        <transition to="RenderPage"/>
    </node>

    <node name="RenderPage">
        <pipelet name="DispatchTemplate">
            <param name="Template" value="product/ProductDetail.isml"/>
        </pipelet>
    </node>
</pipeline>

<!-- 2. Process Pipeline - handles business logic -->
<pipeline name="ProductProcess" type="process">
    <node name="GetProductData">
        <pipelet name="GetProductByID"/>
        <transition condition="found" to="EnrichProductData"/>
        <transition condition="notFound" to="Error"/>
    </node>

    <node name="EnrichProductData">
        <!-- Each pipelet has single responsibility -->
        <pipelet name="CalculateCustomerPrice"/>
        <pipelet name="CheckStockAvailability"/>
        <pipelet name="GetProductRecommendations"/>
        <transition to="Success"/>
    </node>

    <node name="Success">
        <return status="success"/>
    </node>

    <node name="Error">
        <return status="error"/>
    </node>
</pipeline>
```

**Pipelet design principles:**

```java
// Good: Single responsibility pipelet
public class CalculateCustomerPricePipelet extends Pipelet {

    @Inject
    private PricingService pricingService;

    @Override
    public int execute(PipelineDictionary dict) {
        // Clear inputs
        ProductBO product = dict.getRequired("Product");
        CustomerBO customer = dict.getOptional("Customer");

        // Single operation
        Money price = pricingService.calculatePrice(product, customer);

        // Clear output
        dict.put("CustomerPrice", price);

        return PIPELET_NEXT;
    }
}

// Good: Proper error handling
public class GetProductByIDPipelet extends Pipelet {

    @Inject
    private ProductRepository productRepository;

    @Override
    public int execute(PipelineDictionary dict) {
        String productId = dict.getRequired("ProductID");

        ProductBO product = productRepository.getProduct(productId);

        if (product == null) {
            dict.put("ErrorCode", "PRODUCT_NOT_FOUND");
            dict.put("ErrorMessage", "Product with ID " + productId + " not found");
            return PIPELET_ERROR;  // Explicit error exit
        }

        dict.put("Product", product);
        return PIPELET_NEXT;
    }
}
```

**Pipeline design guidelines:**

| Guideline | Description |
|-----------|-------------|
| Separate view/process | View = page flow, Process = business logic |
| Single responsibility | Each pipelet does one thing |
| Clear transitions | Explicit success/error paths |
| Reusable pipelets | Small, focused, parameterized |
| Dictionary discipline | Document required/optional params |
| Error handling | Always handle error cases explicitly |

**When to use pipelines vs. services:**

| Use Case | Pipeline | Service |
|----------|----------|---------|
| User-facing workflows | Yes | |
| Template rendering | Yes | |
| Scheduled jobs | Yes | |
| Reusable business logic | | Yes |
| Complex calculations | | Yes |
| External integrations | | Yes |

Reference: [Guide - Pipeline Style Guide](https://support.intershop.com/kb/index.php/Display/24Y887)
