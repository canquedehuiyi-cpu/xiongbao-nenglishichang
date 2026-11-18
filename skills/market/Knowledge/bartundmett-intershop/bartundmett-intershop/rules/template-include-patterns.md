---
title: Use Correct Include Patterns (isinclude vs ismodule)
impact: MEDIUM
impactDescription: ensures proper template composition and reuse
tags: templates, isml, isinclude, ismodule, composition
---

## Use Correct Include Patterns (isinclude vs ismodule)

**Impact: MEDIUM (ensures proper template composition and reuse)**

Choose the right inclusion mechanism based on your needs: `isinclude` for simple inclusion, `ismodule` for encapsulated components with clear interfaces.

**Incorrect (misusing include mechanisms):**

```html
<%-- Bad: Using isinclude when parameters needed --%>
<isset name="ProductToDisplay" value="#CurrentProduct#" scope="request">
<isset name="ShowPrice" value="#true#" scope="request">
<isset name="ImageSize" value="large" scope="request">
<isinclude template="components/ProductCard">
<%-- Pollutes request scope, unclear interface --%>

<%-- Bad: Overusing ismodule for simple includes --%>
<ismodule template="inc/Separator" name="separator">
<ISseparator>
<%-- Overkill for a simple horizontal rule --%>

<%-- Bad: Missing parameter validation in modules --%>
<ismodule template="components/PriceDisplay" name="PriceDisplay">
    <ISPriceDisplay Product="#Product#">
</ismodule>
<%-- Module template doesn't validate Product is set --%>
```

**Correct (appropriate include patterns):**

```html
<%-- Good: Use isinclude for simple, context-aware includes --%>
<%-- Header assumes CurrentUser, CurrentBasket are in pipeline dict --%>
<isinclude template="inc/Header">

<%-- Good: Use isinclude for layout fragments --%>
<isinclude template="layout/PageStart">
<div class="content">
    ...
</div>
<isinclude template="layout/PageEnd">
```

**Using ismodule for encapsulated components:**

```html
<%-- Good: Define module with clear parameters --%>
<%-- modules/ProductCard.isml --%>
<ismodule template="modules/ProductCard"
          name="ProductCard"
          attribute="Product"
          attribute="ShowPrice"
          attribute="ShowAddToCart"
          attribute="ImageSize">

<%-- Module implementation (ProductCard.isml) --%>
<%--
    ProductCard Module
    Displays a product card with configurable options.

    Attributes:
    - Product (required): ProductBO to display
    - ShowPrice: boolean (default: true)
    - ShowAddToCart: boolean (default: true)
    - ImageSize: "small"|"medium"|"large" (default: "medium")
--%>

<%-- Good: Validate required attributes --%>
<isif condition="#NOT isDefined(Product)#">
    <iserror message="ProductCard: Product attribute is required">
    <isexit>
</isif>

<%-- Good: Set defaults for optional attributes --%>
<isset name="ShowPrice" value="#isDefined(ShowPrice) ? ShowPrice : true#" scope="local">
<isset name="ShowAddToCart" value="#isDefined(ShowAddToCart) ? ShowAddToCart : true#" scope="local">
<isset name="ImageSize" value="#isDefined(ImageSize) ? ImageSize : 'medium'#" scope="local">

<div class="product-card">
    <div class="product-image product-image--<isprint value="#ImageSize#">">
        <isinclude template="components/ProductImage">
    </div>

    <h3 class="product-name">
        <isprint value="#Product:Name#" encoding="html">
    </h3>

    <isif condition="#ShowPrice#">
        <ISPriceDisplay Price="#Product:Price#">
    </isif>

    <isif condition="#ShowAddToCart#">
        <ISAddToCartButton Product="#Product#">
    </isif>
</div>

<%-- Good: Usage with clear interface --%>
<ISProductCard Product="#Product#"
               ShowPrice="#true#"
               ShowAddToCart="#Customer:LoggedIn#"
               ImageSize="large">

<%-- Good: Usage with defaults --%>
<ISProductCard Product="#Product#">
```

**When to use each:**

| Use Case | Mechanism | Reason |
|----------|-----------|--------|
| Layout fragments | `isinclude` | No parameters needed |
| Shared snippets | `isinclude` | Context from pipeline dictionary |
| Configurable components | `ismodule` | Clear parameter interface |
| Reusable widgets | `ismodule` | Encapsulated, documented |
| Simple separators/spacers | `isinclude` | Too simple for module |

**Module attribute best practices:**

```html
<%-- Good: Document all attributes --%>
<%--
    @attribute Product (ProductBO, required) - The product to display
    @attribute Quantity (Integer, optional, default: 1) - Initial quantity
    @attribute Context (String, optional) - "cart"|"listing"|"detail"
--%>

<%-- Good: Type-safe attribute handling --%>
<isset name="Quantity" value="#isDefined(Quantity) AND Quantity GT 0 ? Quantity : 1#" scope="local">

<%-- Good: Handle missing required attributes gracefully --%>
<isif condition="#NOT isDefined(Product) OR Product EQ null#">
    <isif condition="#isDevelopmentMode()#">
        <div class="error">ProductCard: Missing required Product attribute</div>
    </isif>
    <isexit>
</isif>
```

Reference: [ISML Modules Guide](https://knowledge.intershop.com/kb/index.php/Display/24Y887)
