---
title: Use Template Fragment Caching
impact: MEDIUM
impactDescription: reduces server load for static content
tags: templates, isml, caching, performance
---

## Use Template Fragment Caching

**Impact: MEDIUM (reduces server load for static content)**

Use `iscache` to cache template fragments that don't change frequently, reducing server processing time and database queries.

**Incorrect (no caching for static content):**

```html
<%-- Bad: Re-renders on every request --%>
<div class="navigation">
    <%-- Fetches category tree from DB every time --%>
    <isinclude template="components/CategoryNavigation">
</div>

<%-- Bad: Static content rebuilt every request --%>
<footer>
    <isinclude template="inc/FooterLinks">
    <isinclude template="inc/SocialLinks">
    <isinclude template="inc/LegalLinks">
</footer>

<%-- Bad: Product info that rarely changes --%>
<div class="brand-description">
    <isprint value="#Brand:Description#" encoding="html">
</div>
```

**Correct (strategic fragment caching):**

```html
<%-- Good: Cache navigation for 1 hour --%>
<div class="navigation">
    <iscache type="relative" hour="1">
        <isinclude template="components/CategoryNavigation">
    </iscache>
</div>

<%-- Good: Cache footer for 24 hours --%>
<footer>
    <iscache type="relative" day="1">
        <isinclude template="inc/FooterLinks">
        <isinclude template="inc/SocialLinks">
        <isinclude template="inc/LegalLinks">
    </iscache>
</footer>

<%-- Good: Cache with specific time --%>
<div class="promo-banner">
    <iscache type="daily" time="06:00">
        <%-- Expires daily at 6 AM --%>
        <isinclude template="inc/DailyPromotion">
    </iscache>
</div>

<%-- Good: Cache brand content with invalidation key --%>
<iscache type="relative" hour="12" key="#Brand:ID#_#Brand:LastModified#">
    <div class="brand-description">
        <isprint value="#Brand:Description#" encoding="html">
    </div>
</iscache>
```

**Cache key strategies:**

```html
<%-- Good: Vary by locale --%>
<iscache type="relative" hour="1" key="#CurrentLocale#">
    <isinclude template="components/LocalizedNavigation">
</iscache>

<%-- Good: Vary by customer group (B2B/B2C) --%>
<iscache type="relative" minute="30" key="#Customer:CustomerType#">
    <isinclude template="components/PricingInfo">
</iscache>

<%-- Good: Vary by page/context --%>
<iscache type="relative" hour="1" key="#Category:ID#_#CurrentLocale#">
    <div class="category-sidebar">
        <isinclude template="components/CategoryFilters">
    </div>
</iscache>

<%-- Good: Compound key for specific variations --%>
<iscache type="relative" hour="2"
         key="#CurrentChannel#_#CurrentLocale#_#Currency#">
    <isinclude template="components/CurrencySelector">
</iscache>
```

**What NOT to cache:**

```html
<%-- Bad: Never cache user-specific content --%>
<%-- NO: Cart, wishlist, account info --%>
<div class="mini-cart">
    <%-- Must be fresh for current user --%>
    <isinclude template="components/MiniCart">
</div>

<%-- Bad: Never cache with session-dependent data --%>
<%-- NO: CSRF tokens, personalized recommendations --%>

<%-- Bad: Never cache form submissions --%>
<%-- NO: Form results, error messages --%>

<%-- Good: DO cache product info, but NOT for specific user price --%>
<div class="product-detail">
    <%-- Cache static product info --%>
    <iscache type="relative" hour="1" key="#Product:SKU#">
        <div class="product-description">
            <isprint value="#Product:Description#">
        </div>
        <div class="product-specs">
            <isinclude template="product/Specifications">
        </div>
    </iscache>

    <%-- DON'T cache user-specific pricing --%>
    <div class="product-price">
        <isinclude template="product/CustomerPrice">
    </div>
</div>
```

**Cache invalidation patterns:**

```html
<%-- Good: Use version/timestamp in key for invalidation --%>
<iscache type="relative" day="7" key="#CatalogVersion#_#Category:ID#">
    <isinclude template="components/CategoryProducts">
</iscache>

<%-- Good: Short TTL for frequently changing data --%>
<iscache type="relative" minute="5">
    <isinclude template="components/StockStatus">
</iscache>

<%-- Good: Time-based expiry for scheduled content --%>
<iscache type="absolute" date="#PromoEndDate#">
    <isinclude template="promo/LimitedTimeOffer">
</iscache>
```

**Cache configuration matrix:**

| Content Type | TTL | Key Varies By |
|--------------|-----|---------------|
| Navigation | 1 hour | Locale, Channel |
| Footer | 24 hours | Locale |
| Product specs | 2 hours | SKU |
| Category list | 1 hour | Category ID, Locale |
| Stock status | 5 minutes | SKU |
| Promotions | Until end date | Campaign ID |
| User cart | Never cache | - |
| Account info | Never cache | - |

Reference: [ISML Caching Guide](https://knowledge.intershop.com/kb/index.php/Display/24Y887)
