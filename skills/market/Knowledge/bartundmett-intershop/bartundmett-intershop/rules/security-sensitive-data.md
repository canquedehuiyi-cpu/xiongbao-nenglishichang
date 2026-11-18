---
title: Handle Sensitive Data Securely
impact: CRITICAL
impactDescription: protects PII, passwords, and tokens from exposure
tags: security, pii, passwords, encryption, data-protection
---

## Handle Sensitive Data Securely

**Impact: CRITICAL (protects PII, passwords, and tokens from exposure)**

Sensitive data (passwords, tokens, PII, payment info) must be encrypted, masked in logs, and never exposed in URLs or error messages.

**Incorrect (exposing sensitive data):**

```java
// Bad: Logging sensitive data
public void processPayment(PaymentRequest request) {
    logger.info("Processing payment with card: " + request.getCardNumber());
    logger.debug("Full request: " + request.toString());
    // Card number now in log files forever!
}

// Bad: Returning sensitive data in API
@GET
@Path("/user/{id}")
public UserRO getUser(@PathParam("id") String id) {
    UserBO user = userRepository.getUser(id);
    UserRO response = new UserRO();
    response.setPassword(user.getPassword());  // Exposing password hash!
    response.setSocialSecurityNumber(user.getSSN());  // Exposing PII!
    return response;
}

// Bad: Sensitive data in URL
@GET
@Path("/reset-password")
public Response resetPassword(@QueryParam("token") String token,
                              @QueryParam("newPassword") String newPassword) {
    // Password visible in URL, browser history, server logs!
}

// Bad: Sensitive data in error message
public void authenticateUser(String username, String password) {
    if (!isValidPassword(password)) {
        throw new AuthException("Invalid password: " + password);
        // Password exposed in exception/logs!
    }
}
```

**Correct (secure handling):**

```java
// Good: Mask sensitive data in logs
public void processPayment(PaymentRequest request) {
    logger.info("Processing payment for card ending in: {}",
        maskCardNumber(request.getCardNumber()));
}

private String maskCardNumber(String cardNumber) {
    if (cardNumber == null || cardNumber.length() < 4) {
        return "****";
    }
    return "**** **** **** " + cardNumber.substring(cardNumber.length() - 4);
}

// Good: Use separate DTOs for internal and external data
public class UserRO {
    private String id;
    private String username;
    private String email;
    // NO password field!
    // NO SSN field!

    // Only non-sensitive fields exposed
}

public class UserInternalBO {
    private String id;
    private String passwordHash;  // Only for internal use
    private String ssn;           // Only for internal use

    @JsonIgnore  // Never serialize
    public String getPasswordHash() { return passwordHash; }
}

// Good: Sensitive operations via POST body
@POST
@Path("/reset-password")
public Response resetPassword(PasswordResetRequest request) {
    // Password in request body, not URL
    validateToken(request.getToken());
    updatePassword(request.getNewPassword());
    return Response.ok().build();
}

// Good: Generic error messages
public void authenticateUser(String username, String password) {
    if (!isValidCredentials(username, password)) {
        // Generic message - doesn't reveal which part failed
        throw new AuthException("Invalid credentials");
    }
}

// Good: Encrypt sensitive data at rest
@Injectable
public class SensitiveDataService {

    @Inject
    private EncryptionService encryptionService;

    public void storeSensitiveData(String customerId, String ssn) {
        // Encrypt before storing
        String encryptedSSN = encryptionService.encrypt(ssn);
        customerRepository.storeEncryptedSSN(customerId, encryptedSSN);
    }

    public String retrieveSensitiveData(String customerId, AuditContext audit) {
        // Log access for compliance
        auditService.logDataAccess(customerId, "SSN", audit);

        String encryptedSSN = customerRepository.getEncryptedSSN(customerId);
        return encryptionService.decrypt(encryptedSSN);
    }
}
```

**PII handling requirements:**

```java
// Good: PII access controls
public class PIIAccessService {

    @Inject
    private AuthorizationService authService;

    @Inject
    private AuditService auditService;

    public CustomerPII getCustomerPII(String customerId, UserBO requestor) {
        // Check authorization
        if (!authService.canAccessPII(requestor)) {
            throw new ForbiddenException("Not authorized to access PII");
        }

        // Audit the access
        auditService.logPIIAccess(customerId, requestor.getId(), "VIEW");

        // Return with audit trail
        return customerRepository.getPII(customerId);
    }
}
```

**Sensitive data checklist:**

| Data Type | Storage | Logging | API Response |
|-----------|---------|---------|--------------|
| Passwords | Hash + Salt | Never | Never |
| API tokens | Encrypted | Masked | Never |
| Card numbers | Tokenized | Last 4 only | Never full |
| SSN/Tax ID | Encrypted | Never | Authorized only |
| Session IDs | Secure cookie | Never | Never |
| Addresses | Encrypted PII | Masked | Authorized only |

Reference: [OWASP Sensitive Data Exposure](https://owasp.org/www-project-web-security-testing-guide/)
