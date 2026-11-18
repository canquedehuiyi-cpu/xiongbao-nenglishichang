---
title: Implement Internationalization Correctly
impact: HIGH
impactDescription: enables proper multi-language and multi-locale support
tags: i18n, localization, locale, translation, internationalization
---

## Implement Internationalization Correctly

**Impact: HIGH (enables proper multi-language and multi-locale support)**

Intershop applications often serve multiple markets with different languages, currencies, and date formats. Proper internationalization (i18n) ensures consistent user experience across locales.

**Incorrect (hardcoded strings and formats):**

```java
// Bad: Hardcoded strings
public class OrderService {

    public String getOrderStatus(OrderBO order) {
        switch (order.getStatus()) {
            case PENDING: return "Pending";       // Hardcoded!
            case SHIPPED: return "Shipped";       // Not translatable
            case DELIVERED: return "Delivered";
            default: return "Unknown";
        }
    }

    public String formatOrderDate(OrderBO order) {
        // Bad: Hardcoded date format
        SimpleDateFormat sdf = new SimpleDateFormat("MM/dd/yyyy");
        return sdf.format(order.getCreatedDate());  // US format only!
    }

    public String formatPrice(Money price) {
        // Bad: Hardcoded currency format
        return "$" + price.getValue().setScale(2);  // USD only!
    }
}

// Bad: String concatenation for messages
public String getWelcomeMessage(CustomerBO customer) {
    return "Hello, " + customer.getName() + "! You have " +
           customer.getPoints() + " points.";  // Word order varies by language!
}
```

```html
<!-- Bad: Hardcoded text in ISML -->
<h1>Welcome to our store</h1>
<p>Your cart contains <isprint value="#Cart:ItemCount#"/> items.</p>
```

**Correct (properly internationalized):**

```java
// Good: Use localization service for strings
@Injectable
public class OrderService {

    @Inject
    private LocalizationService localizationService;

    @Inject
    private LocaleService localeService;

    public String getOrderStatus(OrderBO order, Locale locale) {
        String statusKey = "order.status." + order.getStatus().name().toLowerCase();
        return localizationService.getString(statusKey, locale);
    }

    public String formatOrderDate(OrderBO order, Locale locale) {
        // Good: Use locale-aware date formatting
        DateTimeFormatter formatter = DateTimeFormatter
            .ofLocalizedDate(FormatStyle.MEDIUM)
            .withLocale(locale);

        return order.getCreatedDate()
            .atZone(ZoneId.systemDefault())
            .format(formatter);
    }

    public String formatPrice(Money price, Locale locale) {
        // Good: Use locale-aware currency formatting
        NumberFormat currencyFormat = NumberFormat.getCurrencyInstance(locale);
        currencyFormat.setCurrency(price.getCurrency());
        return currencyFormat.format(price.getValue());
    }
}

// Good: Message patterns with placeholders
@Injectable
public class MessageService {

    @Inject
    private LocalizationService localizationService;

    public String getWelcomeMessage(CustomerBO customer, Locale locale) {
        // Properties file: welcome.message=Hello, {0}! You have {1,number} points.
        return localizationService.formatMessage(
            "welcome.message",
            locale,
            customer.getName(),
            customer.getPoints()
        );
    }

    public String getOrderConfirmation(OrderBO order, Locale locale) {
        // Properties: order.confirmation=Your order #{0} placed on {1,date,medium}
        // will be delivered by {2,date,full}.
        return localizationService.formatMessage(
            "order.confirmation",
            locale,
            order.getOrderNumber(),
            order.getCreatedDate(),
            order.getEstimatedDelivery()
        );
    }
}

// Good: Localization service implementation
@Injectable
public class LocalizationServiceImpl implements LocalizationService {

    @Inject
    private ResourceBundleManager bundleManager;

    @Override
    public String getString(String key, Locale locale) {
        ResourceBundle bundle = bundleManager.getBundle("messages", locale);
        try {
            return bundle.getString(key);
        } catch (MissingResourceException e) {
            logger.warn("Missing translation for key: {} locale: {}", key, locale);
            return key;  // Return key as fallback
        }
    }

    @Override
    public String formatMessage(String key, Locale locale, Object... args) {
        String pattern = getString(key, locale);
        MessageFormat formatter = new MessageFormat(pattern, locale);
        return formatter.format(args);
    }
}

// Good: Locale-aware repository queries
@Injectable
public class ProductRepository {

    public ProductBO getLocalizedProduct(String sku, Locale locale) {
        // Query localized attributes based on locale
        return query()
            .where("sku", sku)
            .withLocale(locale)
            .withFallback(Locale.ENGLISH)  // Fallback if translation missing
            .findOne();
    }

    public List<ProductBO> searchProducts(String term, Locale locale) {
        // Search in localized fields
        return query()
            .whereLocalized("name", term, locale)
            .orWhereLocalized("description", term, locale)
            .orderByLocalized("name", locale)
            .findAll();
    }
}
```

```html
<!-- Good: ISML with localization tags -->
<h1><istext key="storefront.welcome.title"/></h1>

<!-- Good: Pluralization support -->
<p>
    <istext key="cart.items.count" param0="#Cart:ItemCount#"/>
    <!-- cart.items.count.one=Your cart contains {0} item. -->
    <!-- cart.items.count.other=Your cart contains {0} items. -->
</p>

<!-- Good: Localized date and currency formatting -->
<p>
    <istext key="order.placed.date"/>:
    <isdate value="#Order:CreatedDate#" format="medium"/>
</p>
<p>
    <istext key="order.total"/>:
    <ismoney value="#Order:Total#"/>
</p>
```

**Properties file organization:**

```
resources/
├── messages.properties                 # Default (fallback)
├── messages_de.properties              # German
├── messages_de_AT.properties           # Austrian German
├── messages_fr.properties              # French
├── messages_zh_CN.properties           # Simplified Chinese
└── messages_zh_TW.properties           # Traditional Chinese
```

**Locale resolution chain:**

```java
// Good: Proper locale resolution
@Injectable
public class LocaleResolver {

    public Locale resolveLocale(HttpServletRequest request) {
        // 1. Check URL parameter (for testing/override)
        String paramLocale = request.getParameter("locale");
        if (isValidLocale(paramLocale)) {
            return Locale.forLanguageTag(paramLocale);
        }

        // 2. Check user preference (if authenticated)
        CustomerBO customer = getAuthenticatedCustomer(request);
        if (customer != null && customer.getPreferredLocale() != null) {
            return customer.getPreferredLocale();
        }

        // 3. Check session
        Locale sessionLocale = (Locale) request.getSession()
            .getAttribute("USER_LOCALE");
        if (sessionLocale != null) {
            return sessionLocale;
        }

        // 4. Check Accept-Language header
        Locale headerLocale = request.getLocale();
        if (isSupportedLocale(headerLocale)) {
            return headerLocale;
        }

        // 5. Fall back to channel default
        return channelService.getCurrentChannel().getDefaultLocale();
    }
}
```

**i18n best practices:**

| Area | Recommendation |
|------|----------------|
| Strings | Never hardcode, use resource bundles |
| Dates | Use DateTimeFormatter with locale |
| Numbers | Use NumberFormat with locale |
| Currency | Use Money objects with currency |
| Plurals | Use ICU MessageFormat |
| Sorting | Use Collator for locale-aware sorting |

Reference: [ICM Localization Guide](https://knowledge.intershop.com/kb/index.php/Display/2X2893)
