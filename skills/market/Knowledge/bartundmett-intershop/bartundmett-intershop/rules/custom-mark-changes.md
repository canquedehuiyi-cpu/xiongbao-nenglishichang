---
title: Mark All Customizations with Comments
impact: HIGH
impactDescription: enables easier tracking during upgrades and code reviews
tags: customization, documentation, migration, comments
---

## Mark All Customizations with Comments

**Impact: HIGH (enables easier tracking during upgrades and code reviews)**

When modifications to standard files are absolutely unavoidable, mark all customizations with standardized comments. This enables automated detection during upgrades and helps reviewers understand what has been changed.

**Incorrect (unmarked changes):**

```java
// Original file with silent modifications
public class OrderProcessPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        Order order = dict.get("Order");

        // Some new logic added without marking
        if (order.isB2BOrder()) {
            applyB2BDiscount(order);
        }

        return PIPELET_NEXT;
    }
}
```

**Correct (clearly marked customizations):**

```java
public class OrderProcessPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        Order order = dict.get("Order");

        // CUSTOMIZATION BEGIN - ACME-1234: B2B discount handling
        // Added by: John Doe, 2026-01-15
        // Reason: Apply automatic discount for B2B orders per business requirement
        if (order.isB2BOrder()) {
            applyB2BDiscount(order);
        }
        // CUSTOMIZATION END - ACME-1234

        return PIPELET_NEXT;
    }
}
```

**For templates (ISML/HTML):**

```html
<!-- CUSTOMIZATION BEGIN - ACME-1234: Custom header banner -->
<div class="custom-banner">
    <isinclude template="inc/CustomBanner"/>
</div>
<!-- CUSTOMIZATION END - ACME-1234 -->
```

**For pipelines (XML):**

```xml
<!-- CUSTOMIZATION BEGIN - ACME-1234: Additional validation node -->
<node name="ValidateB2BOrder">
    <pipelet name="ValidateB2BOrderPipelet"/>
</node>
<!-- CUSTOMIZATION END - ACME-1234 -->
```

**Comment format standards:**

```
// CUSTOMIZATION BEGIN - <TICKET-ID>: <Brief description>
// Added by: <Developer name>, <Date>
// Reason: <Why this change was necessary>
<code changes>
// CUSTOMIZATION END - <TICKET-ID>
```

**Benefits:**
- Automated scripts can find all customizations with `grep "CUSTOMIZATION"`
- Clear audit trail for compliance and reviews
- Easier merge conflict resolution during upgrades
- Git can produce better diffs when original context is preserved

Reference: [Guide - Intershop PWA - Customizations](https://knowledge.intershop.com/kb/index.php/Display/30B854)
