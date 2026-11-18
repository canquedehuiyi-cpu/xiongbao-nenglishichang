---
title: Never Log Sensitive Data
impact: CRITICAL
impactDescription: prevents data breaches through log exposure
tags: logging, security, pii, sensitive-data, compliance
---

## Never Log Sensitive Data

**Impact: CRITICAL (prevents data breaches through log exposure)**

Logs often end up in multiple systems (files, aggregators, SIEM). Never log passwords, tokens, PII, or financial data. Mask sensitive fields before logging.

**Incorrect (logging sensitive data):**

```java
// Bad: Logging password
logger.info("User login attempt: username={}, password={}", username, password);

// Bad: Logging full credit card
logger.info("Processing payment for card: {}", cardNumber);

// Bad: Logging API token
logger.debug("Calling external API with token: {}", apiToken);

// Bad: Logging full request with sensitive fields
logger.info("Received request: {}", request.toString());

// Bad: Logging exception with sensitive context
try {
    authenticateUser(credentials);
} catch (Exception e) {
    logger.error("Auth failed for: " + credentials, e);  // Credentials in log!
}

// Bad: Logging PII
logger.info("Customer details: name={}, ssn={}, dob={}",
    customer.getName(), customer.getSSN(), customer.getDateOfBirth());
```

**Correct (masking sensitive data):**

```java
// Good: Never log passwords - log attempt only
logger.info("User login attempt", kv("username", username));

// Good: Mask credit card numbers
logger.info("Processing payment",
    kv("cardLast4", maskCard(cardNumber)),
    kv("amount", amount));

private String maskCard(String cardNumber) {
    if (cardNumber == null || cardNumber.length() < 4) {
        return "****";
    }
    return "**** **** **** " + cardNumber.substring(cardNumber.length() - 4);
}

// Good: Never log tokens - log presence/validity only
logger.debug("Calling external API",
    kv("hasToken", apiToken != null),
    kv("tokenPrefix", apiToken != null ? apiToken.substring(0, 4) + "..." : null));

// Good: Use safe toString() that masks sensitive fields
logger.info("Received request", kv("request", request.toSafeString()));

public class PaymentRequest {
    private String cardNumber;
    private String cvv;
    private Money amount;

    public String toSafeString() {
        return String.format("PaymentRequest{cardLast4=%s, amount=%s}",
            maskCard(cardNumber), amount);
    }

    // Exclude sensitive fields from standard toString
    @Override
    public String toString() {
        return toSafeString();  // Always safe
    }
}

// Good: Safe exception logging
try {
    authenticateUser(credentials);
} catch (AuthenticationException e) {
    logger.warn("Authentication failed",
        kv("username", credentials.getUsername()),  // Username OK
        kv("reason", e.getReason()));               // Password NOT logged
}

// Good: PII masking
logger.info("Customer lookup",
    kv("customerId", customer.getId()),
    kv("nameInitials", getInitials(customer.getName())));
    // SSN, DOB never logged

private String getInitials(String name) {
    return Arrays.stream(name.split(" "))
        .map(part -> part.substring(0, 1))
        .collect(Collectors.joining("."));
}
```

**Centralized masking utility:**

```java
public class LogMasker {

    private static final Pattern EMAIL_PATTERN =
        Pattern.compile("([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})");

    private static final Pattern CARD_PATTERN =
        Pattern.compile("\\b\\d{13,19}\\b");

    private static final Pattern SSN_PATTERN =
        Pattern.compile("\\b\\d{3}-\\d{2}-\\d{4}\\b");

    public static String mask(String input) {
        if (input == null) return null;

        String masked = input;

        // Mask email addresses
        masked = EMAIL_PATTERN.matcher(masked)
            .replaceAll(m -> m.group(1).charAt(0) + "***@" + m.group(2));

        // Mask card numbers
        masked = CARD_PATTERN.matcher(masked)
            .replaceAll(m -> "**** **** **** " + m.group().substring(m.group().length() - 4));

        // Mask SSNs
        masked = SSN_PATTERN.matcher(masked)
            .replaceAll("***-**-****");

        return masked;
    }
}

// Usage
logger.info("Processing data: {}", LogMasker.mask(rawData));
```

**Sensitive data checklist:**

| Data Type | Log? | If Needed |
|-----------|------|-----------|
| Passwords | Bad: Never | Log attempt only |
| API tokens | Bad: Never | Log presence |
| Session IDs | Bad: Never | Log hash |
| Credit cards | Bad: Never | Last 4 digits |
| CVV/CVC | Bad: Never | Never |
| SSN/Tax ID | Bad: Never | Never |
| Full names | ⚠️ Careful | Initials if needed |
| Email | ⚠️ Careful | Masked or ID |
| Phone | ⚠️ Careful | Last 4 digits |
| Address | ⚠️ Careful | City/country only |
| DOB | Bad: Never | Year only if needed |
| Medical | Bad: Never | Never |

**Logback filter for safety:**

```xml
<!-- logback.xml - Last line of defense -->
<appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
    <encoder>
        <pattern>%d{ISO8601} [%thread] %-5level %logger{36} - %msg%n</pattern>
    </encoder>
    <!-- Mask patterns in all log output -->
    <filter class="com.mycompany.logging.SensitiveDataMaskingFilter"/>
</appender>
```

Reference: [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
