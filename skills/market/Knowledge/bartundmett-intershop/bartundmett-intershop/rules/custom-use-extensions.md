---
title: Use Business Object Extensions for Custom Behavior
impact: CRITICAL
impactDescription: enables upgrade-safe customization with minimal coupling
tags: customization, business-objects, extensions, upgrade-safe
---

## Use Business Object Extensions for Custom Behavior

**Impact: CRITICAL (enables upgrade-safe customization with minimal coupling)**

Business object extensions allow adding functionality to existing business objects without modifying the original code. Extensions are the primary mechanism for upgrade-safe customization in ICM.

**Incorrect (subclassing or modifying existing BO):**

```java
// Bad: Subclassing standard BO - breaks on upgrades
public class CustomProductBOImpl extends ProductBOImpl {

    private CustomDataService customDataService;

    @Override
    public String getDescription() {
        // Adding custom logic by overriding
        return super.getDescription() + getCustomSuffix();
    }
}
```

**Correct (using extension pattern):**

```java
// 1. Define extension interface in API cartridge (bc_custom_product)
// capi/CustomProductExtension.java
public interface CustomProductExtension extends BusinessObjectExtension<ProductBO> {

    /**
     * Returns enhanced description with custom suffix.
     */
    String getEnhancedDescription();

    /**
     * Returns custom product metadata.
     */
    CustomMetadata getCustomMetadata();
}

// 2. Implement in internal package (bc_custom_product_orm)
// internal/CustomProductExtensionImpl.java
public class CustomProductExtensionImpl implements CustomProductExtension {

    private final ProductBO productBO;

    @Inject
    private CustomMetadataService metadataService;

    public CustomProductExtensionImpl(ProductBO productBO) {
        this.productBO = productBO;
    }

    @Override
    public String getEnhancedDescription() {
        return productBO.getDescription() + getCustomSuffix();
    }

    @Override
    public CustomMetadata getCustomMetadata() {
        return metadataService.getMetadata(productBO.getSKU());
    }

    private String getCustomSuffix() {
        // Custom logic here
        return " - Available Now";
    }
}

// 3. Register extension in component file
// Using the extension:
ProductBO product = productRepository.getProduct(sku);
CustomProductExtension ext = product.getExtension(CustomProductExtension.class);
String enhanced = ext.getEnhancedDescription();
```

**Benefits:**
- Original business objects remain untouched
- Extensions are loaded dynamically via the extension framework
- Easy to disable/enable extensions per application type
- Clear separation between standard and custom code

Reference: [Guide - Business Objects](https://knowledge.intershop.com/kb/index.php/Display/U25993)
