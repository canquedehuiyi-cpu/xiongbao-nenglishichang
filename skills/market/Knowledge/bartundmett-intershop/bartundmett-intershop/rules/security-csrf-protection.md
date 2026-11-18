---
title: Implement CSRF Protection
impact: CRITICAL
impactDescription: prevents cross-site request forgery attacks
tags: security, csrf, tokens, web-security
---

## Implement CSRF Protection

**Impact: CRITICAL (prevents cross-site request forgery attacks)**

Cross-Site Request Forgery (CSRF) attacks trick authenticated users into performing unintended actions. ICM applications must implement proper CSRF protection for all state-changing operations.

**Incorrect (vulnerable to CSRF):**

```java
// Bad: No CSRF token validation
@RestController
public class OrderController {

    @PostMapping("/orders")
    public ResponseEntity<OrderRO> createOrder(@RequestBody OrderData data) {
        // No CSRF token check - vulnerable!
        return orderService.create(data);
    }

    @DeleteMapping("/orders/{id}")
    public ResponseEntity<Void> deleteOrder(@PathVariable String id) {
        // State-changing operation without CSRF protection
        orderService.delete(id);
        return ResponseEntity.ok().build();
    }
}

// Bad: GET request for state-changing operation
@GetMapping("/orders/{id}/cancel")
public ResponseEntity<Void> cancelOrder(@PathVariable String id) {
    // GET should be idempotent - this is vulnerable via image tags, links
    orderService.cancel(id);
    return ResponseEntity.ok().build();
}
```

```html
<!-- Bad: Form without CSRF token -->
<form action="/orders" method="POST">
    <input type="text" name="productId" />
    <button type="submit">Order</button>
</form>
```

**Correct (CSRF protected):**

```java
// Good: CSRF token service
@Injectable
public class CsrfTokenService {

    private static final String CSRF_TOKEN_ATTR = "CSRF_TOKEN";
    private static final int TOKEN_VALIDITY_MINUTES = 30;

    @Inject
    private SecureRandomService secureRandom;

    public CsrfToken generateToken(HttpSession session) {
        String tokenValue = secureRandom.generateToken(32);
        Instant expiry = Instant.now().plus(TOKEN_VALIDITY_MINUTES, ChronoUnit.MINUTES);

        CsrfToken token = new CsrfToken(tokenValue, expiry);
        session.setAttribute(CSRF_TOKEN_ATTR, token);

        return token;
    }

    public boolean validateToken(HttpServletRequest request) {
        HttpSession session = request.getSession(false);
        if (session == null) {
            return false;
        }

        CsrfToken storedToken = (CsrfToken) session.getAttribute(CSRF_TOKEN_ATTR);
        if (storedToken == null || storedToken.isExpired()) {
            return false;
        }

        // Check header first (for AJAX), then form parameter
        String providedToken = request.getHeader("X-CSRF-Token");
        if (providedToken == null) {
            providedToken = request.getParameter("_csrf");
        }

        if (providedToken == null) {
            return false;
        }

        // Constant-time comparison to prevent timing attacks
        return MessageDigest.isEqual(
            storedToken.getValue().getBytes(StandardCharsets.UTF_8),
            providedToken.getBytes(StandardCharsets.UTF_8)
        );
    }
}

// Good: CSRF validation filter
@Injectable
public class CsrfFilter implements Filter {

    private static final Set<String> SAFE_METHODS =
        Set.of("GET", "HEAD", "OPTIONS", "TRACE");

    @Inject
    private CsrfTokenService csrfService;

    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest request = (HttpServletRequest) req;
        HttpServletResponse response = (HttpServletResponse) res;

        // Skip CSRF check for safe (read-only) methods
        if (SAFE_METHODS.contains(request.getMethod())) {
            chain.doFilter(request, response);
            return;
        }

        // Validate CSRF token for state-changing requests
        if (!csrfService.validateToken(request)) {
            response.setStatus(HttpServletResponse.SC_FORBIDDEN);
            response.getWriter().write("{\"error\": \"Invalid CSRF token\"}");
            return;
        }

        chain.doFilter(request, response);
    }
}

// Good: REST controller with proper HTTP methods
@RestController
public class OrderController {

    @PostMapping("/orders")
    public ResponseEntity<OrderRO> createOrder(
            @RequestBody OrderData data,
            HttpServletRequest request) {
        // CSRF validated by filter for POST
        return ResponseEntity.ok(orderService.create(data));
    }

    @DeleteMapping("/orders/{id}")
    public ResponseEntity<Void> deleteOrder(@PathVariable String id) {
        // DELETE is state-changing, CSRF validated by filter
        orderService.delete(id);
        return ResponseEntity.ok().build();
    }

    // Good: Use POST for state-changing operations, not GET
    @PostMapping("/orders/{id}/cancel")
    public ResponseEntity<Void> cancelOrder(@PathVariable String id) {
        orderService.cancel(id);
        return ResponseEntity.ok().build();
    }
}
```

```html
<!-- Good: ISML template with CSRF token -->
<form action="#URL(Action('ProcessOrder'))#" method="POST">
    <input type="hidden" name="_csrf" value="#CSRF_TOKEN#" />
    <input type="text" name="productId" />
    <button type="submit">Order</button>
</form>
```

```javascript
// Good: AJAX requests with CSRF token header
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

fetch('/api/orders', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken  // Include token in header
    },
    body: JSON.stringify(orderData)
});
```

**Double-submit cookie pattern (alternative):**

```java
// Good: Double-submit cookie implementation
@Injectable
public class DoubleSubmitCsrfService {

    private static final String CSRF_COOKIE = "XSRF-TOKEN";
    private static final String CSRF_HEADER = "X-XSRF-TOKEN";

    public void setCsrfCookie(HttpServletResponse response) {
        String token = generateSecureToken();

        Cookie cookie = new Cookie(CSRF_COOKIE, token);
        cookie.setHttpOnly(false);  // Must be readable by JavaScript
        cookie.setSecure(true);
        cookie.setPath("/");
        cookie.setSameSite("Strict");

        response.addCookie(cookie);
    }

    public boolean validateDoubleSubmit(HttpServletRequest request) {
        String cookieToken = getCookieValue(request, CSRF_COOKIE);
        String headerToken = request.getHeader(CSRF_HEADER);

        if (cookieToken == null || headerToken == null) {
            return false;
        }

        return MessageDigest.isEqual(
            cookieToken.getBytes(StandardCharsets.UTF_8),
            headerToken.getBytes(StandardCharsets.UTF_8)
        );
    }
}
```

**CSRF protection strategies:**

| Strategy | Pros | Cons |
|----------|------|------|
| Synchronizer token | Most secure | Requires session storage |
| Double-submit cookie | Stateless | Vulnerable if subdomain XSS |
| SameSite cookies | Simple | Browser support varies |
| Custom headers | Works for AJAX | Doesn't protect forms |

Reference: [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
