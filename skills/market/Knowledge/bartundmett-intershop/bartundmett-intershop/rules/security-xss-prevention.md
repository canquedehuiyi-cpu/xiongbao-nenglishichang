---
title: Prevent Cross-Site Scripting (XSS) Attacks
impact: CRITICAL
impactDescription: prevents script injection in rendered output
tags: security, xss, templates, encoding, sanitization
---

## Prevent Cross-Site Scripting (XSS) Attacks

**Impact: CRITICAL (prevents script injection in rendered output)**

All user-supplied data must be properly encoded before rendering in HTML, JavaScript, or other contexts. XSS attacks can steal sessions, deface sites, or spread malware.

**Incorrect (XSS vulnerabilities):**

```html
<%-- Bad: ISML: Unescaped output - XSS vulnerable --%>
<div class="product-name">
    <isprint value="#Product:Name#">
</div>

<%-- Bad: Direct injection into JavaScript --%>
<script>
    var productName = '<isprint value="#Product:Name#">';
    // Attacker input: '</script><script>alert("XSS")</script>'
</script>

<%-- Bad: Unescaped URL parameter --%>
<a href="/search?q=<isprint value="#SearchQuery#">">Search</a>
```

```java
// Bad: Java: Returning unescaped HTML
@GET
@Path("/product/{sku}/description")
@Produces(MediaType.TEXT_HTML)
public String getProductDescription(@PathParam("sku") String sku) {
    ProductBO product = productRepository.getProduct(sku);
    // User-controlled description rendered as HTML!
    return "<div>" + product.getDescription() + "</div>";
}
```

**Correct (XSS prevention):**

```html
<%-- Good: ISML: Use encoding attribute --%>
<div class="product-name">
    <isprint value="#Product:Name#" encoding="html">
</div>

<%-- Good: ISML: Use isset with proper encoding for attributes --%>
<input type="text" value="<isprint value="#SearchQuery#" encoding="htmlattr">">

<%-- Good: JavaScript context: Use JSON encoding --%>
<script>
    var productData = <isprint value="#ProductJSON#" encoding="jsonvalue">;
    // Properly escaped as JSON
</script>

<%-- Good: URL context: Use URL encoding --%>
<a href="/search?q=<isprint value="#SearchQuery#" encoding="url">">Search</a>

<%-- Good: CSS context (if absolutely necessary) --%>
<div style="background-color: <isprint value="#BgColor#" encoding="css">;">
```

```java
// Good: Java: Use proper encoding utilities
@GET
@Path("/product/{sku}/description")
@Produces(MediaType.TEXT_HTML)
public String getProductDescription(@PathParam("sku") String sku) {
    ProductBO product = productRepository.getProduct(sku);

    // HTML encode user content
    String safeDescription = HtmlUtils.htmlEscape(product.getDescription());

    return "<div>" + safeDescription + "</div>";
}

// Good: REST API: Return data as JSON (automatically encoded)
@GET
@Path("/product/{sku}")
@Produces(MediaType.APPLICATION_JSON)
public ProductRO getProduct(@PathParam("sku") String sku) {
    ProductBO product = productRepository.getProduct(sku);

    // JSON serialization handles encoding
    return productMapper.toRO(product);
}

// Good: Rich text: Use HTML sanitizer for allowed tags
public String sanitizeRichText(String userHtml) {
    PolicyFactory policy = Sanitizers.FORMATTING
        .and(Sanitizers.LINKS)
        .and(Sanitizers.BLOCKS);

    return policy.sanitize(userHtml);
}
```

**Encoding contexts:**

| Context | ISML Encoding | Java Utility |
|---------|---------------|--------------|
| HTML body | `encoding="html"` | `HtmlUtils.htmlEscape()` |
| HTML attribute | `encoding="htmlattr"` | `HtmlUtils.htmlEscape()` |
| JavaScript | `encoding="jsonvalue"` | JSON serializer |
| URL parameter | `encoding="url"` | `URLEncoder.encode()` |
| CSS value | `encoding="css"` | Whitelist approach |

**Content Security Policy (CSP) header:**

```java
// Good: Add CSP header in REST responses
@Provider
public class SecurityHeadersFilter implements ContainerResponseFilter {

    @Override
    public void filter(ContainerRequestContext request, ContainerResponseContext response) {
        response.getHeaders().add("Content-Security-Policy",
            "default-src 'self'; " +
            "script-src 'self'; " +
            "style-src 'self' 'unsafe-inline'; " +
            "img-src 'self' data:; " +
            "frame-ancestors 'none';");

        response.getHeaders().add("X-Content-Type-Options", "nosniff");
        response.getHeaders().add("X-Frame-Options", "DENY");
        response.getHeaders().add("X-XSS-Protection", "1; mode=block");
    }
}
```

Reference: [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
