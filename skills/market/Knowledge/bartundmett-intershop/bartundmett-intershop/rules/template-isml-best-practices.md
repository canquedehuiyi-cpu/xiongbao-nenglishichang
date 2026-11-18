---
title: Follow ISML Template Coding Standards
impact: MEDIUM
impactDescription: ensures maintainable and performant templates
tags: templates, isml, frontend, coding-standards
---

## Follow ISML Template Coding Standards

**Impact: MEDIUM (ensures maintainable and performant templates)**

ISML templates should follow consistent coding standards for maintainability, performance, and security.

**Incorrect (poor ISML practices):**

```html
<%-- Bad: Business logic in templates --%>
<isif condition="#Product:Price:Value GT 100 AND Customer:Segment EQ 'VIP' AND NOT Product:OnSale#">
    <isset name="DiscountedPrice" value="#Product:Price:Value * 0.9#" scope="request">
    <isset name="FinalPrice" value="#DiscountedPrice - (DiscountedPrice * TaxRate)#" scope="request">
    <%-- Complex calculation belongs in pipelet/service! --%>
</isif>

<%-- Bad: Hardcoded strings --%>
<button>Add to Cart</button>
<p>Free shipping on orders over $50!</p>

<%-- Bad: Inline styles --%>
<div style="background-color: #f0f0f0; padding: 20px; margin: 10px;">

<%-- Bad: Unescaped output --%>
<div class="description"><isprint value="#Product:Description#"></div>

<%-- Bad: Deep nesting makes template unreadable --%>
<isif condition="#Condition1#">
    <isif condition="#Condition2#">
        <isif condition="#Condition3#">
            <isif condition="#Condition4#">
                <%-- 4 levels deep! --%>
            </isif>
        </isif>
    </isif>
</isif>
```

**Correct (ISML best practices):**

```html
<%-- Good: Use includes for reusable components --%>
<isinclude template="components/ProductPrice">

<%-- Good: Localized strings --%>
<button><istext key="button.addToCart" /></button>
<p><istext key="shipping.freeOver" param1="#FreeShippingThreshold#" /></p>

<%-- Good: CSS classes instead of inline styles --%>
<div class="product-card">

<%-- Good: Always encode output --%>
<div class="description">
    <isprint value="#Product:Description#" encoding="html">
</div>

<%-- Good: Flatten conditions or use early returns --%>
<isif condition="#NOT CanDisplayProduct#">
    <isinclude template="components/ProductUnavailable">
    <isexit>
</isif>

<%-- Now we know CanDisplayProduct is true --%>
<div class="product-detail">
    <isinclude template="product/ProductHeader">
    <isinclude template="product/ProductGallery">
    <isinclude template="product/ProductInfo">
</div>
```

**Template organization:**

```
templates/
├── default/
│   ├── page/               # Full page templates
│   │   ├── ProductDetail.isml
│   │   └── CategoryListing.isml
│   ├── components/         # Reusable components
│   │   ├── ProductCard.isml
│   │   ├── ProductPrice.isml
│   │   └── AddToCartButton.isml
│   ├── includes/           # Shared includes
│   │   ├── Header.isml
│   │   └── Footer.isml
│   └── modules/            # ISModule definitions
│       └── ProductModule.isml
```

**Comments and documentation:**

```html
<%-- Good: Document template purpose and expected inputs --%>
<%--
    ProductCard.isml
    Displays a product card for listings and recommendations.

    Required pipeline dictionary:
    - Product (ProductBO): The product to display
    - ShowQuickView (Boolean): Whether to show quick view button

    Optional:
    - ImageSize (String): "small", "medium", "large" (default: "medium")
--%>

<%-- Good: Mark customizations clearly --%>
<!-- CUSTOMIZATION BEGIN - ACME-1234: Custom badge display -->
<isif condition="#Product:hasCustomBadge#">
    <div class="custom-badge"><isprint value="#Product:CustomBadge#" encoding="html"></div>
</isif>
<!-- CUSTOMIZATION END - ACME-1234 -->
```

**Template performance:**

```html
<%-- Good: Avoid loops within loops when possible --%>
<%-- Bad: Nested loop recalculates on each iteration
<isloop iterator="Products" alias="Product">
    <isloop iterator="Product:Categories" alias="Category">
--%>

<%-- Good: Use iselse for mutually exclusive conditions --%>
<isif condition="#Product:InStock#">
    <span class="in-stock"><istext key="stock.available" /></span>
<iselseif condition="#Product:BackorderedAvailable#">
    <span class="backorder"><istext key="stock.backorder" /></span>
<iselse>
    <span class="out-of-stock"><istext key="stock.unavailable" /></span>
</isif>

<%-- Good: Use iscache for cacheable fragments --%>
<iscache type="relative" hour="1">
<isinclude template="components/CategoryNavigation">
</iscache>
```

**ISML best practices summary:**

| Practice | Description |
|----------|-------------|
| No business logic | Keep calculations in pipelets/services |
| Localize strings | Use istext for all user-visible text |
| Encode output | Always use encoding attribute |
| Use includes | Break into reusable components |
| Flatten nesting | Use isexit for early returns |
| Document inputs | Comment expected dictionary contents |
| Cache fragments | Use iscache for static content |

Reference: [ISML Template Guide](https://knowledge.intershop.com/kb/index.php/Display/24Y887)
