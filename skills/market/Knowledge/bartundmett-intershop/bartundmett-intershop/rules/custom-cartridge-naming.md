---
title: Follow Cartridge Naming Conventions
impact: CRITICAL
impactDescription: ensures clear code organization and avoids conflicts
tags: customization, cartridge, naming, architecture
---

## Follow Cartridge Naming Conventions

**Impact: CRITICAL (ensures clear code organization and avoids conflicts)**

Cartridges must follow strict naming conventions based on their architectural layer and purpose. Proper naming prevents conflicts with Intershop standard cartridges and makes the codebase navigable.

**Incorrect (arbitrary naming):**

```
// Bad: Bad cartridge names
myproject_product/           // No layer prefix
custom_stuff/                // Vague, no structure
ProductExtensions/           // Capitalized, no prefix
bc_product_custom/           // Conflicts with standard bc_ namespace
```

**Correct (following layer conventions):**

```
// Good: Good cartridge names for customer projects

// Use vendor prefix to differentiate from Intershop cartridges
acme_pf_core/               // Platform layer - core infrastructure
acme_bc_product/            // Business component - product extensions (API)
acme_bc_product_orm/        // Business component - ORM implementation
acme_as_storefront/         // Application - storefront specific
acme_app_b2b/               // Application type - B2B specific
acme_ft_pricing/            // Feature - pricing customizations
```

**Layer prefixes and their purposes:**

| Prefix | Layer | Typical Contents |
|--------|-------|------------------|
| `pf_` | Platform | Java code, 3rd party libraries, core infrastructure |
| `bc_` | Business Component | Business objects, pipelets, process pipelines |
| `as_` | Application Set | Application-specific customizations |
| `app_` | Application Type | Templates, pagelets, webforms |
| `ft_` | Feature | Optional feature modules |

**Java package naming must match cartridge hierarchy:**

```java
// Cartridge: acme_bc_product
// Package structure:
com.acme.component.product.capi     // Public API
com.acme.component.product.internal // Internal implementation
com.acme.component.product.dbinit   // Database initialization
com.acme.component.product.pipelet  // Pipelets
```

Reference: [Concept - Cartridge](https://knowledge.intershop.com/kb/index.php/Display/308Z99)
