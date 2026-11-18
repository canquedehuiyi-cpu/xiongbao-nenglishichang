---
title: Minimize Session Size
impact: MEDIUM
impactDescription: reduces memory footprint and improves scalability
tags: performance, session, memory, scalability
---

## Minimize Session Size

**Impact: MEDIUM (reduces memory footprint and improves scalability)**

Large session objects consume memory, slow down serialization/replication, and reduce server scalability. Keep sessions lean with only essential data.

**Incorrect (bloated session):**

```java
// Bad: Storing entire business objects in session
public class CartController {

    public void addToCart(ProductBO product, HttpSession session) {
        List<ProductBO> cart = (List<ProductBO>) session.getAttribute("cart");
        if (cart == null) {
            cart = new ArrayList<>();
        }
        cart.add(product);  // Full BO with all associations!
        session.setAttribute("cart", cart);
    }
}

// Bad: Storing search results in session
public class SearchController {

    public void search(String query, HttpSession session) {
        List<ProductBO> results = searchService.search(query);  // 1000 products!
        session.setAttribute("searchResults", results);
        session.setAttribute("searchQuery", query);
    }
}

// Bad: Storing non-serializable objects
public class UserController {

    public void login(UserBO user, HttpSession session) {
        session.setAttribute("user", user);  // May have non-serializable fields
        session.setAttribute("connection", databaseConnection);  // Never do this!
    }
}

// Bad: Never cleaning up session data
public class WizardController {

    public void step1(WizardData data, HttpSession session) {
        session.setAttribute("wizard_step1", data);
    }

    public void step2(WizardData data, HttpSession session) {
        session.setAttribute("wizard_step2", data);
        // step1 data still in session, never removed
    }
}
```

**Correct (lean session):**

```java
// Good: Store only IDs/references, load on demand
@Injectable
public class CartSessionService {

    @Inject
    private CartRepository cartRepository;

    public void addToCart(String productSku, String sessionId) {
        // Store only cart ID in session
        String cartId = getOrCreateCartId(sessionId);
        cartRepository.addItem(cartId, productSku);
    }

    public CartBO getCart(HttpSession session) {
        String cartId = (String) session.getAttribute("cartId");
        if (cartId == null) {
            return CartBO.empty();
        }
        return cartRepository.getCart(cartId);  // Load fresh from DB/cache
    }

    private String getOrCreateCartId(String sessionId) {
        // Cart persisted externally, only ID in session
        return "cart-" + sessionId;
    }
}

// Good: Use lightweight session DTOs
public class SessionUserData implements Serializable {

    private static final long serialVersionUID = 1L;

    private final String userId;
    private final String username;
    private final String customerNumber;
    private final Set<String> roles;
    private final String locale;

    // Only essential, immutable data
    public static SessionUserData from(UserBO user) {
        return new SessionUserData(
            user.getId(),
            user.getUsername(),
            user.getCustomer().getCustomerNumber(),
            user.getRoles().stream().map(RoleBO::getName).collect(toSet()),
            user.getPreferredLocale()
        );
    }
}

@Injectable
public class UserSessionService {

    public void login(UserBO user, HttpSession session) {
        SessionUserData sessionData = SessionUserData.from(user);
        session.setAttribute("userData", sessionData);

        // Store timestamp for session validation
        session.setAttribute("loginTime", Instant.now().toEpochMilli());
    }
}

// Good: Paginate search results, don't store
@Injectable
public class SearchController {

    @Inject
    private SearchService searchService;

    public SearchResultRO search(SearchRequest request) {
        // Execute search each time with pagination
        SearchResult result = searchService.search(
            request.getQuery(),
            request.getPage(),
            request.getPageSize()
        );

        // Return result, don't store in session
        return new SearchResultRO(
            result.getItems(),
            result.getTotalCount(),
            result.getPage()
        );
    }
}

// Good: Clean up temporary session data
@Injectable
public class WizardController {

    private static final String WIZARD_KEY = "wizardData";

    public void step1(WizardData data, HttpSession session) {
        WizardState state = new WizardState();
        state.setStep1Data(data);
        session.setAttribute(WIZARD_KEY, state);
    }

    public void step2(WizardData data, HttpSession session) {
        WizardState state = (WizardState) session.getAttribute(WIZARD_KEY);
        state.setStep2Data(data);
    }

    public void complete(HttpSession session) {
        WizardState state = (WizardState) session.getAttribute(WIZARD_KEY);
        processWizard(state);

        // Clean up after completion
        session.removeAttribute(WIZARD_KEY);
    }

    public void cancel(HttpSession session) {
        session.removeAttribute(WIZARD_KEY);
    }
}

// Good: Monitor session size
@Injectable
public class SessionSizeMonitor {

    private static final int MAX_SESSION_SIZE_KB = 100;

    public void checkSessionSize(HttpSession session) {
        try {
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            ObjectOutputStream oos = new ObjectOutputStream(baos);

            Enumeration<String> names = session.getAttributeNames();
            while (names.hasMoreElements()) {
                String name = names.nextElement();
                Object value = session.getAttribute(name);
                if (value instanceof Serializable) {
                    oos.writeObject(value);
                }
            }

            int sizeKB = baos.size() / 1024;
            if (sizeKB > MAX_SESSION_SIZE_KB) {
                logger.warn("Session {} exceeds size limit: {}KB",
                    session.getId(), sizeKB);
            }

        } catch (IOException e) {
            logger.debug("Could not measure session size", e);
        }
    }
}
```

**Session data guidelines:**

| Data Type | Store in Session | Alternative |
|-----------|------------------|-------------|
| User ID | Good: Yes | - |
| User roles | Good: Yes (as Set<String>) | - |
| Locale/Currency | Good: Yes | - |
| Full User BO | Bad: No | Load by ID |
| Cart items | Bad: No | External storage + ID |
| Search results | Bad: No | Re-query with pagination |
| File uploads | Bad: No | Temp files |
| Large collections | Bad: No | Cache/DB |

Reference: [ICM Session Management](https://knowledge.intershop.com/kb/index.php/Display/2Y9813)
