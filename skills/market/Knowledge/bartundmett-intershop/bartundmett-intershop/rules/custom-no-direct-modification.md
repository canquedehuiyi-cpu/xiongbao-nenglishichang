---
title: Avoid Direct Modification of Standard Files
impact: CRITICAL
impactDescription: prevents migration conflicts and upgrade issues
tags: customization, migration, upgrade-safe, best-practice
---

## Avoid Direct Modification of Standard Files

**Impact: CRITICAL (prevents migration conflicts and upgrade issues)**

The best customization is no customization. Intershop is a feature-rich product with extensive configuration options. Always check if you can achieve your goal through configuration before writing custom code. Direct modification of standard files creates merge conflicts during upgrades.

**Incorrect (directly modifying standard cartridge files):**

```java
// Modifying bc_product/javasource/com/intershop/component/product/internal/ProductBOImpl.java
// NEVER DO THIS - will cause merge conflicts on every upgrade
public class ProductBOImpl extends AbstractPersistentObjectBO implements ProductBO {

    @Override
    public Money getPrice() {
        // Custom price logic added directly to standard class
        Money basePrice = super.getPrice();
        return applyCustomDiscount(basePrice);  // Bad: Direct modification
    }
}
```

**Correct (using extension mechanism):**

```java
// Create custom cartridge: app_custom_product
// javasource/com/mycompany/product/capi/CustomProductBOExtension.java
public interface CustomProductBOExtension extends BusinessObjectExtension<ProductBO> {
    Money getCustomPrice();
}

// javasource/com/mycompany/product/internal/CustomProductBOExtensionImpl.java
public class CustomProductBOExtensionImpl implements CustomProductBOExtension {

    private final ProductBO productBO;

    public CustomProductBOExtensionImpl(ProductBO productBO) {
        this.productBO = productBO;
    }

    @Override
    public Money getCustomPrice() {
        Money basePrice = productBO.getPrice();
        return applyCustomDiscount(basePrice);  // Good: Extension pattern
    }
}
```

**Key principle:** If a customization seems absolutely necessary, contact Intershop first. If your feature is standard-worthy, Intershop may build it as part of the product.

Reference: [Guide - Intershop Commerce Platform - Customization Options](https://knowledge.intershop.com/kb/index.php/Display/29230E)
