---
title: Optimize Template Loops for Performance
impact: MEDIUM
impactDescription: reduces page render time for large datasets
tags: templates, isml, performance, loops, optimization
---

## Optimize Template Loops for Performance

**Impact: MEDIUM (reduces page render time for large datasets)**

Template loops can significantly impact rendering performance. Avoid expensive operations inside loops and minimize loop nesting.

**Incorrect (inefficient loops):**

```html
<%-- Bad: Expensive operations inside loop --%>
<isloop iterator="Products" alias="Product" counter="Counter">
    <%-- Database call on every iteration! --%>
    <isset name="ProductStock" value="#stockService:getStock(Product:SKU)#" scope="request">

    <%-- Complex calculation repeated --%>
    <isset name="DiscountedPrice" value="#calculateDiscount(Product, Customer)#" scope="request">

    <%-- Nested loop multiplies work --%>
    <isloop iterator="AllCategories" alias="Category">
        <isif condition="#Product:Categories:contains(Category)#">
            <span class="category"><isprint value="#Category:Name#"></span>
        </isif>
    </isloop>
</isloop>

<%-- Bad: Not limiting results --%>
<isloop iterator="AllProducts" alias="Product">
    <%-- Could be 10,000+ products! --%>
</isloop>

<%-- Bad: Repeating same calculation --%>
<isloop iterator="Products" alias="Product">
    <isset name="FormattedDate" value="#formatDate(CurrentDate, Locale)#" scope="request">
    <%-- Same result every iteration! --%>
</isloop>
```

**Correct (optimized loops):**

```html
<%-- Good: Pre-fetch data before loop (in pipelet) --%>
<%-- Pipeline: Fetch all stock levels in one batch query
     Dict: ProductStockMap = Map<SKU, StockLevel> --%>

<isloop iterator="Products" alias="Product">
    <isset name="Stock" value="#ProductStockMap:get(Product:SKU)#" scope="local">
    <div class="stock-level">
        <isprint value="#Stock:Available#">
    </div>
</isloop>

<%-- Good: Calculate once, use in loop --%>
<isset name="FormattedDate" value="#formatDate(CurrentDate, Locale)#" scope="local">
<isset name="ShowPricing" value="#Customer:LoggedIn AND Customer:CanSeePrices#" scope="local">

<isloop iterator="Products" alias="Product">
    <div class="product">
        <isprint value="#FormattedDate#">  <%-- Reuse pre-calculated value --%>
        <isif condition="#ShowPricing#">
            <isprint value="#Product:Price#">
        </isif>
    </div>
</isloop>

<%-- Good: Pre-compute category membership (in pipelet) --%>
<%-- Dict: Product:CategorySet = Set of category IDs --%>
<isloop iterator="Products" alias="Product">
    <div class="categories">
        <isloop iterator="Product:CategorySet" alias="CategoryId">
            <span class="category"><isprint value="#CategoryId#"></span>
        </isloop>
    </div>
</isloop>

<%-- Good: Limit results --%>
<isloop iterator="Products" alias="Product" begin="0" end="19">
    <%-- Only first 20 products --%>
</isloop>

<%-- Good: Use loop status for alternating styles --%>
<isloop iterator="Products" alias="Product" status="LoopStatus">
    <div class="product <isif condition="#LoopStatus:odd#">odd</isif>">
        <isprint value="#Product:Name#">
    </div>
</isloop>

<%-- Good: Early exit from loop when target found --%>
<isloop iterator="Products" alias="Product">
    <isif condition="#Product:Featured#">
        <div class="featured-product">
            <isinclude template="components/FeaturedProduct">
        </div>
        <isbreak>  <%-- Found featured product, exit loop --%>
    </isif>
</isloop>
```

**Avoiding nested loops:**

```html
<%-- Bad: O(n×m) complexity --%>
<isloop iterator="Orders" alias="Order">
    <isloop iterator="AllProducts" alias="Product">
        <isif condition="#Order:ContainsProduct(Product)#">
            ...
        </isif>
    </isloop>
</isloop>

<%-- Good: Pre-build lookup in pipelet, O(n) --%>
<%-- Pipeline builds: Order:ProductSet for each order --%>
<isloop iterator="Orders" alias="Order">
    <isloop iterator="Order:LineItems" alias="LineItem">
        <%-- Direct access, no search --%>
        <isprint value="#LineItem:Product:Name#">
    </isloop>
</isloop>
```

**Loop optimization checklist:**

| Issue | Solution |
|-------|----------|
| Database call in loop | Batch fetch before loop |
| Complex calculation | Pre-compute before loop |
| Nested loops | Flatten or pre-index data |
| Unlimited results | Use begin/end limits |
| Repeated same value | Calculate once, store in variable |
| Full iteration needed | Use isbreak when target found |

**When to move logic to pipelet:**

```java
// Good: Pipelet pre-computes data for template
public class PrepareProductListPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        List<ProductBO> products = dict.get("Products");

        // Batch fetch stock levels (1 query instead of N)
        Map<String, Integer> stockMap = stockService.getStockLevels(
            products.stream().map(ProductBO::getSKU).collect(Collectors.toList())
        );
        dict.put("ProductStockMap", stockMap);

        // Pre-calculate discounts
        CustomerBO customer = dict.get("Customer");
        Map<String, Money> priceMap = pricingService.calculatePrices(products, customer);
        dict.put("ProductPriceMap", priceMap);

        return PIPELET_NEXT;
    }
}
```

Reference: [ISML Performance Guide](https://knowledge.intershop.com/kb/index.php/Display/24Y887)
