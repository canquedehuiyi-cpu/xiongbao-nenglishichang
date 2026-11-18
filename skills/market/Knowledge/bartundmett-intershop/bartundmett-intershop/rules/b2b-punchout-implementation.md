---
title: Implement Punchout with Proper User Roles and Security
impact: CRITICAL
impactDescription: enables secure B2B procurement integration
tags: b2b, punchout, oci, cxml, security, procurement
---

## Implement Punchout with Proper User Roles and Security

**Impact: CRITICAL (enables secure B2B procurement integration)**

OCI and cXML Punchout enable B2B customers to browse your catalog from their procurement systems. Proper implementation requires correct user roles, security configuration, and session handling.

**Incorrect (insecure punchout implementation):**

```java
// Bad: Using regular user authentication for punchout
public class PunchoutAuthPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        String username = dict.get("USERNAME");
        String password = dict.get("PASSWORD");

        // Regular authentication - wrong for punchout!
        UserBO user = authService.authenticate(username, password);

        // No role validation
        dict.put("User", user);

        return PIPELET_NEXT;
    }
}

// Bad: Exposing full storefront to punchout users
// No restriction on accessible features
```

**Correct (secure punchout with proper roles):**

```java
// 1. Punchout-specific authentication handler
public class OciPunchoutAuthHandler {

    @Inject
    private PunchoutUserService punchoutUserService;

    @Inject
    private PunchoutSessionManager sessionManager;

    public PunchoutSession authenticate(PunchoutRequest request) {
        // Validate punchout credentials
        PunchoutCredentials credentials = extractCredentials(request);

        // Get punchout user with restricted permissions
        PunchoutUserBO user = punchoutUserService.getPunchoutUser(
            credentials.getUsername(),
            credentials.getCustomerID()
        );

        // Verify user has OCI punchout role
        if (!user.hasRole(PunchoutRoles.OCI_USER)) {
            throw new PunchoutAuthenticationException("User not authorized for OCI punchout");
        }

        // Create punchout session with limited scope
        PunchoutSession session = sessionManager.createSession(user, request);
        session.setAllowedOperations(PunchoutOperations.BROWSE, PunchoutOperations.ADD_TO_CART);

        return session;
    }
}

// 2. Role-based access control for punchout
public enum PunchoutRoles {
    OCI_USER,           // Basic OCI punchout access
    CXML_USER,          // cXML punchout access
    PUNCHOUT_ADMIN      // Can configure punchout settings
}

// 3. Punchout-specific pipelet with security checks
public class OciProductDetailsPipelet extends Pipelet {

    @Inject
    private PunchoutSecurityService securityService;

    @Override
    public int execute(PipelineDictionary dict) {
        // Verify this is a valid punchout session
        PunchoutSession session = dict.get("PunchoutSession");
        if (!securityService.validatePunchoutSession(session)) {
            return PIPELET_ERROR;
        }

        String productId = dict.get("PRODUCTID");
        ProductBO product = productRepository.getProduct(productId);

        // Format response according to OCI standard
        OciProductRecord record = ociFormatter.formatProduct(
            product,
            session.getPricingContext()
        );

        dict.put("OciProductRecord", record);
        return PIPELET_NEXT;
    }
}

// 4. Configure punchout URL mapping
// punchoutconfiguration.properties
// APP_B2B_OCI_USER=oci_punchout_user
// punchout.oci.fields=NEW_ITEM-VENDORMAT,NEW_ITEM-DESCRIPTION,NEW_ITEM-QUANTITY,...
```

**Field configuration for OCI:**

```properties
# punchoutconfiguration.properties

# Define which fields are returned in OCI format
punchout.oci.fields.NEW_ITEM-VENDORMAT=${product.sku}
punchout.oci.fields.NEW_ITEM-DESCRIPTION=${product.name}
punchout.oci.fields.NEW_ITEM-QUANTITY=${quantity}
punchout.oci.fields.NEW_ITEM-UNIT=${product.unit}
punchout.oci.fields.NEW_ITEM-PRICE=${price.value}
punchout.oci.fields.NEW_ITEM-CURRENCY=${price.currency}
punchout.oci.fields.NEW_ITEM-LEADTIME=${product.leadTime}

# Custom field mapping
punchout.oci.mapping.UNIT.PCE=EA
punchout.oci.mapping.UNIT.KG=KGM
```

**Punchout functions to implement:**

| Function | Purpose | Security Level |
|----------|---------|----------------|
| CATALOG | Browse catalog | Read-only |
| VALIDATE | Get current price/availability | Read-only |
| DETAIL | Get product details | Read-only |
| BACKGROUND_SEARCH | Cross-catalog search | Read-only |
| SOURCING | Submit cart to procurement | Write (limited) |

Reference: [Concept - OCI Punchout](https://knowledge.intershop.com/kb/index.php/Display/2934C1)
