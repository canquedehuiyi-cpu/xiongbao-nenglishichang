# Intershop ICM Best Practices Guide

**Version:** 1.0.0
**Organization:** Intershop Engineering
**Date:** January 2026

> **Note:**
> This document is mainly for agents and LLMs to follow when maintaining,
> generating, or refactoring Intershop Commerce Management (ICM) codebases.
> Humans may also find it useful, but guidance here is optimized for automation
> and consistency by AI-assisted workflows.

---

## Abstract

Comprehensive best practices guide for Intershop Commerce Management (ICM) backend development, designed for AI agents and LLMs. Contains 65 rules across 18 categories, prioritized by impact from critical (customization patterns, performance optimization, B2B features, security) to incremental (advanced patterns). Each rule includes detailed explanations, real-world examples comparing incorrect vs. correct implementations, and specific impact metrics to guide automated refactoring and code generation.

---

## Table of Contents

1. [Customization Patterns](#1-customization-patterns) - **CRITICAL**
2. [Performance Optimization](#2-performance-optimization) - **CRITICAL**
3. [State Management & Data Flow](#3-state-management--data-flow) - **CRITICAL**
4. [B2B Features](#4-b2b-features) - **CRITICAL**
5. [REST API Development](#5-rest-api-development) - **HIGH**
6. [Cartridge Architecture](#6-cartridge-architecture) - **HIGH**
7. [Database & Persistence](#7-database--persistence) - **MEDIUM-HIGH**
8. [Pipeline & Pipelet Development](#8-pipeline--pipelet-development) - **MEDIUM**
9. [Dependency Injection & Guice](#9-dependency-injection--guice) - **MEDIUM**
10. [Deployment & DevOps](#10-deployment--devops) - **LOW-MEDIUM**
11. [Testing](#11-testing) - **HIGH**
12. [Security](#12-security) - **CRITICAL**
13. [Logging & Observability](#13-logging--observability) - **MEDIUM**
14. [ISML Templates](#14-isml-templates) - **MEDIUM**
15. [Job & Batch Processing](#15-job--batch-processing) - **MEDIUM**
16. [Events & Messaging](#16-events--messaging) - **MEDIUM**
17. [ImpEx Data Exchange](#17-impex-data-exchange) - **MEDIUM**
18. [Search](#18-search) - **HIGH**
19. [References](#references)

---

## 1. Customization Patterns

**Impact:** CRITICAL

Proper customization patterns ensure upgrade-safe modifications, minimize merge conflicts, and maintain long-term maintainability. Poor customization is the #1 source of migration pain.

### 1.1 Avoid Direct Modification of Standard Files

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
        return applyCustomDiscount(basePrice);  // Direct modification
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
        return applyCustomDiscount(basePrice);  // Extension pattern
    }
}
```

**Key principle:** If a customization seems absolutely necessary, contact Intershop first. If your feature is standard-worthy, Intershop may build it as part of the product.

Reference: [Guide - Intershop Commerce Platform - Customization Options](https://knowledge.intershop.com/kb/index.php/Display/29230E)

---

### 1.2 Use Business Object Extensions for Custom Behavior

**Impact: CRITICAL (enables upgrade-safe customization with minimal coupling)**

Business object extensions allow adding functionality to existing business objects without modifying the original code. Extensions are the primary mechanism for upgrade-safe customization in ICM.

**Incorrect (subclassing or modifying existing BO):**

```java
// Subclassing standard BO - breaks on upgrades
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

---

### 1.3 Follow Cartridge Naming Conventions

**Impact: CRITICAL (ensures clear code organization and avoids conflicts)**

Cartridges must follow strict naming conventions based on their architectural layer and purpose. Proper naming prevents conflicts with Intershop standard cartridges and makes the codebase navigable.

**Incorrect (arbitrary naming):**

```
// Bad cartridge names
myproject_product/           // No layer prefix
custom_stuff/                // Vague, no structure
ProductExtensions/           // Capitalized, no prefix
bc_product_custom/           // Conflicts with standard bc_ namespace
```

**Correct (following layer conventions):**

```
// Good cartridge names for customer projects

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

---

### 1.4 Mark All Customizations with Comments

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

---

### 1.5 Prefer Microservices for Complex Customizations

**Impact: CRITICAL (reduces coupling and enables independent deployment)**

Additional microservices are the recommended approach for extending the Intershop Commerce Platform. They can provide additional REST APIs, handle business events, or integrate with external systems without modifying the ICM core.

**Incorrect (implementing everything inside ICM):**

```java
// Complex integration logic inside ICM cartridge
public class ExternalERPSyncPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        Order order = dict.get("Order");

        // Complex ERP integration logic directly in pipelet
        ERPClient client = new ERPClient(getERPConfig());
        ERPOrder erpOrder = transformToERPFormat(order);

        try {
            client.connect();
            client.authenticate();
            client.submitOrder(erpOrder);
            client.waitForConfirmation();
            order.setERPOrderID(erpOrder.getConfirmationID());
        } finally {
            client.disconnect();
        }

        return PIPELET_NEXT;
    }
}
```

**Correct (microservice architecture):**

```java
// ICM side - simple REST call to microservice
public class ERPIntegrationPipelet extends Pipelet {

    @Inject
    private ERPIntegrationService erpService;

    @Override
    public int execute(PipelineDictionary dict) {
        Order order = dict.get("Order");

        // Simple async call to microservice
        erpService.submitOrderAsync(order.getOrderID());

        return PIPELET_NEXT;
    }
}

// Microservice (separate project/container)
@RestController
@RequestMapping("/api/erp")
public class ERPOrderController {

    @Autowired
    private ERPClient erpClient;

    @Autowired
    private OrderEventPublisher eventPublisher;

    @PostMapping("/orders/{orderId}")
    public ResponseEntity<ERPResult> submitOrder(@PathVariable String orderId) {
        // All complex ERP logic in dedicated microservice
        Order order = fetchOrderFromICM(orderId);
        ERPOrder erpOrder = transformToERPFormat(order);

        ERPResult result = erpClient.submit(erpOrder);

        // Publish event for ICM to consume
        eventPublisher.publishOrderSubmitted(orderId, result);

        return ResponseEntity.ok(result);
    }
}
```

**When to use microservices:**

| Use Case | Microservice | ICM Cartridge |
|----------|--------------|---------------|
| Complex external integrations | Yes | |
| Long-running processes | Yes | |
| Compute-intensive operations | Yes | |
| Simple business logic extension | | Yes |
| UI customizations | | Yes |
| Core commerce modifications | | Yes (via extensions) |

**Benefits:**
- Independent deployment and scaling
- Technology flexibility (not limited to Java)
- Easier testing and debugging
- Reduced ICM upgrade complexity
- Better fault isolation

Reference: [Guide - Intershop Commerce Platform - Customization Options](https://knowledge.intershop.com/kb/index.php/Display/29230E)

---

## 2. Performance Optimization

**Impact:** CRITICAL

Optimizing database queries, caching strategies, memory management, and connection pooling directly impacts user experience and system scalability.

### 2.1 Use Caching for Expensive Operations

**Impact: CRITICAL (10-100x improvement for repeated queries)**

Expensive database queries, external service calls, and computed results should be cached at the appropriate level. ICM provides multiple caching mechanisms depending on the scope and lifetime of the data.

**Incorrect (repeated expensive operations):**

```java
// Fetching same data multiple times per request
public class ProductDetailsPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        String sku = dict.get("SKU");

        // Each call queries the database
        ProductBO product = productRepository.getProduct(sku);
        CategoryBO category = categoryRepository.getCategory(product.getCategoryID());
        PriceBO price = priceService.calculatePrice(product);
        StockBO stock = stockService.getStock(product);

        // Later in the same request, same data fetched again
        if (product.isConfigurable()) {
            // Another database query for the same product!
            ProductBO sameProduct = productRepository.getProduct(sku);
            // ...
        }

        return PIPELET_NEXT;
    }
}
```

**Correct (using appropriate caching):**

```java
// 1. Per-request caching with pipeline dictionary
public class ProductDetailsPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        String sku = dict.get("SKU");

        // Cache key for this request
        String cacheKey = "ProductDetails:" + sku;

        // Check if already fetched in this request
        ProductDetails details = dict.get(cacheKey);
        if (details == null) {
            details = fetchProductDetails(sku);
            dict.put(cacheKey, details);  // Cache for this request
        }

        return PIPELET_NEXT;
    }
}

// 2. Cross-request caching with CacheMgr
@Inject
private CacheMgr cacheMgr;

public ProductBO getProduct(String sku) {
    Cache cache = cacheMgr.getCache("ProductCache");
    String cacheKey = "product:" + sku;

    ProductBO product = cache.get(cacheKey);
    if (product == null) {
        product = productRepository.getProduct(sku);
        cache.put(cacheKey, product, 300);  // Cache for 5 minutes
    }
    return product;
}

// 3. For computed/expensive operations, use memoization
public class PriceCalculationService {

    private final Cache priceCache;

    @Inject
    public PriceCalculationService(CacheMgr cacheMgr) {
        this.priceCache = cacheMgr.getCache("PriceCache");
    }

    public Money calculateComplexPrice(ProductBO product, CustomerBO customer) {
        String cacheKey = buildCacheKey(product, customer);

        return priceCache.computeIfAbsent(cacheKey, () -> {
            // Expensive calculation only runs once per cache period
            return performComplexPriceCalculation(product, customer);
        });
    }
}
```

**Caching levels in ICM:**

| Level | Scope | Use Case |
|-------|-------|----------|
| Pipeline Dictionary | Single request | Avoid duplicate queries in one request |
| CacheMgr | Cross-request | Product data, configurations |
| Redis/External | Cross-node | Session data, distributed caching |

Reference: [Concept - Technical Architecture of ICM 11+](https://knowledge.intershop.com/kb/index.php/Display/30983L)

---

### 2.2 Optimize Database Queries

**Impact: CRITICAL (2-50x improvement in response times)**

Database queries are often the primary bottleneck in ICM applications. Use efficient query patterns, proper indexing hints, and avoid N+1 query problems.

**Incorrect (N+1 query problem):**

```java
// N+1 queries - one query per product in loop
public List<ProductDTO> getProductsWithPrices(Collection<String> skus) {
    List<ProductDTO> results = new ArrayList<>();

    for (String sku : skus) {
        // Query 1: Get product
        ProductBO product = productRepository.getProduct(sku);

        // Query 2: Get price (per product!)
        PriceBO price = priceRepository.getPrice(product);

        // Query 3: Get stock (per product!)
        StockBO stock = stockRepository.getStock(product);

        results.add(new ProductDTO(product, price, stock));
    }

    return results;  // Total: 1 + (3 x N) queries!
}
```

**Correct (batch queries):**

```java
// Batch queries - constant number of queries regardless of size
public List<ProductDTO> getProductsWithPrices(Collection<String> skus) {
    // Query 1: Get all products in one query
    Map<String, ProductBO> products = productRepository.getProductsBySKUs(skus);

    // Query 2: Get all prices in one query
    Map<String, PriceBO> prices = priceRepository.getPricesForProducts(products.keySet());

    // Query 3: Get all stocks in one query
    Map<String, StockBO> stocks = stockRepository.getStocksForProducts(products.keySet());

    // Combine in memory
    return skus.stream()
        .map(sku -> new ProductDTO(
            products.get(sku),
            prices.get(sku),
            stocks.get(sku)
        ))
        .collect(Collectors.toList());  // Total: 3 queries regardless of N
}
```

**Common anti-patterns to avoid:**

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| N+1 queries | O(N) database calls | Batch fetching |
| SELECT * | Loads unnecessary data | Projections |
| No pagination | Memory issues | LIMIT/OFFSET |
| Missing indexes | Full table scans | Query hints, DBA review |
| Lazy loading in loops | Hidden N+1 | Eager fetch or batch |

Reference: [Overview - Persistent Object Layer](https://support.intershop.com/kb/index.php/Display/278Z46)

---

### 2.3 Use Asynchronous Processing for Non-Critical Operations

**Impact: HIGH (reduces response times by 30-70% for complex workflows)**

Operations that don't affect the immediate response should be processed asynchronously. This includes logging, analytics, notifications, and external system updates.

**Incorrect (synchronous blocking operations):**

```java
// All operations block the response
public class OrderPlacementPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        Order order = dict.get("Order");

        // Core operation - must be synchronous
        orderRepository.save(order);

        // These block the response but don't need to!
        emailService.sendOrderConfirmation(order);      // 200ms
        analyticsService.trackOrderPlaced(order);       // 100ms
        erpService.notifyNewOrder(order);               // 500ms
        inventoryService.reserveStock(order);           // 300ms
        auditService.logOrderCreation(order);           // 50ms

        // Total: 1150ms of unnecessary blocking!
        return PIPELET_NEXT;
    }
}
```

**Correct (non-blocking async operations):**

```java
// Non-critical operations run asynchronously
public class OrderPlacementPipelet extends Pipelet {

    @Inject
    private AsyncExecutor asyncExecutor;

    @Inject
    private EventPublisher eventPublisher;

    @Override
    public int execute(PipelineDictionary dict) {
        Order order = dict.get("Order");

        // Core operation - synchronous
        orderRepository.save(order);

        // Publish event for async handlers
        eventPublisher.publish(new OrderPlacedEvent(order.getOrderID()));

        // Or use direct async execution
        asyncExecutor.submit(() -> emailService.sendOrderConfirmation(order));
        asyncExecutor.submit(() -> analyticsService.trackOrderPlaced(order));

        // Response returns immediately
        return PIPELET_NEXT;
    }
}
```

**When to use async vs sync:**

| Operation Type | Approach | Reason |
|----------------|----------|--------|
| Order creation | Sync | Must complete before response |
| Payment processing | Sync | User needs immediate feedback |
| Email notifications | Async | Can tolerate delay |
| Analytics/logging | Async | Not user-visible |
| ERP sync | Async | External system, may be slow |
| Stock reservation | Depends | Critical = sync, soft = async |

Reference: [Concept - Technical Architecture of ICM 11+](https://knowledge.intershop.com/kb/index.php/Display/30983L)

---

### 2.4-2.8 Additional Performance Rules

Additional performance optimization rules are documented in:
- `rules/perf-lazy-loading.md` - Lazy loading patterns
- `rules/perf-batch-processing.md` - Batch processing optimization
- `rules/perf-connection-pooling.md` - Connection pool configuration
- `rules/perf-memory-management.md` - Memory optimization
- `rules/perf-session-size.md` - Session size management

---

## 3. State Management & Data Flow

**Impact:** CRITICAL

Proper business object handling, repository patterns, and data flow architecture are essential for maintainable and performant ICM applications.

### 3.1 Use Repository Pattern for Data Access

**Impact: CRITICAL (ensures proper lifecycle management and testability)**

Repositories provide a clean abstraction for data access, making code testable and maintainable. Always inject repositories rather than using direct query APIs.

See `rules/state-repository-pattern.md` for complete implementation.

### 3.2 Maintain BO/PO Separation

**Impact: CRITICAL (ensures clean architecture)**

Business Objects (BO) contain business logic while Persistent Objects (PO) handle database mapping. Never expose POs outside the persistence layer.

See `rules/state-bo-po-separation.md` for complete implementation.

---

## 4. B2B Features

**Impact:** CRITICAL

B2B-specific features like punchout, customer-specific pricing, organization hierarchy, approval workflows, budget management, quote management, and role-based access control require careful implementation to meet enterprise requirements.

### 4.1-4.7 B2B Implementation Rules

B2B features are documented in detail in:
- `rules/b2b-punchout-implementation.md` - Punchout catalog integration
- `rules/b2b-customer-pricing.md` - Customer-specific pricing
- `rules/b2b-organization-hierarchy.md` - Organization structure management
- `rules/b2b-approval-workflows.md` - Multi-level approval processes
- `rules/b2b-budget-management.md` - Budget tracking and enforcement
- `rules/b2b-quote-management.md` - Quote lifecycle management
- `rules/b2b-user-roles.md` - Role-based access control

---

## 5. REST API Development

**Impact:** HIGH

Properly designed REST resources with correct handlers, resource objects, authentication, pagination, error handling, versioning, and HATEOAS ensure secure and maintainable API endpoints.

### 5.1 Authenticate REST Resources

**Impact: CRITICAL (prevents unauthorized access)**

All REST resources must verify authentication and authorization inside each method.

```java
@DELETE
@Path("/{orderId}")
public Response deleteOrder(@PathParam("orderId") String orderId) {
    // 1. Authenticate
    UserBO currentUser = authService.getCurrentUser();
    if (currentUser == null) {
        throw new WebApplicationException(Response.Status.UNAUTHORIZED);
    }

    // 2. Authorize
    OrderBO order = orderRepository.getOrder(orderId);
    if (!authzService.canDelete(currentUser, order)) {
        throw new WebApplicationException(Response.Status.FORBIDDEN);
    }

    // 3. Execute
    orderRepository.deleteOrder(orderId);
    return Response.ok().build();
}
```

### 5.2-5.7 Additional REST API Rules

REST API development rules are documented in:
- `rules/rest-authentication.md` - Token-based authentication
- `rules/rest-resource-objects.md` - Response object design
- `rules/rest-handlers.md` - Request handler implementation
- `rules/rest-pagination.md` - Paginated responses
- `rules/rest-error-handling.md` - Error response format
- `rules/rest-versioning.md` - API versioning strategies
- `rules/rest-hateoas.md` - Hypermedia controls

---

## 6. Cartridge Architecture

**Impact:** HIGH

Correct cartridge organization, dependency management, and layering patterns form the foundation of maintainable ICM customizations.

### 6.1 Separate API and Implementation Cartridges

**Impact: HIGH (enables clean architecture)**

See `rules/cartridge-api-separation.md` for detailed guidance.

---

## 7. Database & Persistence

**Impact:** MEDIUM-HIGH

Proper use of persistent objects, ORM patterns, transaction management, optimistic locking, PO lifecycle, and database initialization ensures data integrity and performance.

### 7.1-7.4 Database Rules

Database and persistence rules are documented in:
- `rules/db-dbprepare-migration.md` - Database schema migrations
- `rules/db-transaction-management.md` - Transaction boundaries
- `rules/db-optimistic-locking.md` - Concurrent update handling
- `rules/db-po-lifecycle.md` - Persistent object lifecycle

---

## 8. Pipeline & Pipelet Development

**Impact:** MEDIUM

Following pipeline best practices, proper transaction handling, and error handling ensures maintainable business logic implementation.

### 8.1-8.3 Pipeline Rules

Pipeline development rules are documented in:
- `rules/pipeline-best-practices.md` - General pipeline guidelines
- `rules/pipeline-error-handling.md` - Error management
- `rules/pipeline-transactions.md` - Transaction management

---

## 9. Dependency Injection & Guice

**Impact:** MEDIUM

Proper use of Guice for dependency injection enables testability and extensibility of ICM components.

### 9.1 Use Guice for Dependency Injection

See `rules/guice-dependency-injection.md` for Guice configuration and injection patterns.

---

## 10. Deployment & DevOps

**Impact:** LOW-MEDIUM

Container-based deployment, Kubernetes configuration, and CI/CD integration patterns for reliable releases.

### 10.1 Container Deployment

See `rules/devops-container-deployment.md` for Docker and Kubernetes deployment patterns.

---

## 11. Testing

**Impact:** HIGH

Comprehensive testing strategies including unit tests, integration tests, REST API testing, mock repositories, and test data builders ensure code quality and reliability.

### 11.1-11.5 Testing Rules

Complete testing guidance is available in:
- `rules/test-unit-test-services.md` - Unit testing patterns
- `rules/test-integration-pipelines.md` - Pipeline integration tests
- `rules/test-mock-repositories.md` - Repository mocking
- `rules/test-test-data-builders.md` - Test data creation
- `rules/test-rest-api-testing.md` - REST API testing

---

## 12. Security

**Impact:** CRITICAL

Input validation, SQL injection prevention, XSS prevention, sensitive data handling, and access control patterns are essential for secure applications.

### 12.1 Validate All External Input

**Impact: CRITICAL (prevents injection attacks and data corruption)**

All input from external sources must be validated before processing.

```java
// DTO with validation annotations
public class ProductCreateRO {

    @NotBlank(message = "SKU is required")
    @Size(min = 3, max = 50, message = "SKU must be 3-50 characters")
    @Pattern(regexp = "^[A-Z0-9-]+$", message = "SKU must contain only uppercase letters, numbers, and hyphens")
    private String sku;

    @NotBlank(message = "Name is required")
    @Size(min = 1, max = 255, message = "Name must be 1-255 characters")
    private String name;

    @NotNull(message = "Price is required")
    @DecimalMin(value = "0.01", message = "Price must be positive")
    private BigDecimal price;
}
```

### 12.2 Use Parameterized Queries to Prevent SQL Injection

**Impact: CRITICAL (prevents SQL injection attacks)**

Never concatenate user input into SQL queries.

```java
// Named parameters
public List<ProductBO> searchProducts(String name) {
    String hql = "FROM ProductPO p WHERE p.name LIKE :namePattern";

    Query query = queryManager.createQuery(hql);
    query.setParameter("namePattern", "%" + sanitizeWildcard(name) + "%");

    return query.list();
}
```

### 12.3-12.5 Additional Security Rules

Complete security guidance is available in:
- `rules/security-input-validation.md` - Input validation patterns
- `rules/security-sql-injection.md` - SQL injection prevention
- `rules/security-xss-prevention.md` - XSS prevention
- `rules/security-sensitive-data.md` - Sensitive data handling
- `rules/security-access-control.md` - Access control implementation

---

## 13. Logging & Observability

**Impact:** MEDIUM

Structured logging, correlation IDs, appropriate log levels, and avoiding sensitive data in logs enable effective debugging and monitoring.

### 13.1-13.4 Logging Rules

Complete logging guidance is available in:
- `rules/logging-structured-logging.md` - Structured logging patterns
- `rules/logging-correlation-ids.md` - Request tracing
- `rules/logging-log-levels.md` - Log level guidelines
- `rules/logging-no-sensitive-data.md` - Sensitive data protection

---

## 14. ISML Templates

**Impact:** MEDIUM

ISML template best practices, include patterns, loop optimization, and fragment caching improve frontend performance and maintainability.

### 14.1-14.4 ISML Template Rules

Complete ISML guidance is available in:
- `rules/template-isml-best-practices.md` - General template guidelines
- `rules/template-include-patterns.md` - Include vs module patterns
- `rules/template-loop-optimization.md` - Loop performance
- `rules/template-caching.md` - Fragment caching

---

## 15. Job & Batch Processing

**Impact:** MEDIUM

Proper job implementation with progress tracking, error handling, checkpointing, and cancellation support enables reliable batch operations.

### 15.1-15.2 Job Processing Rules

Complete job processing guidance is available in:
- `rules/job-implementation.md` - Job structure and monitoring
- `rules/job-error-handling.md` - Error handling and recovery

---

## 16. Events & Messaging

**Impact:** MEDIUM

Domain event publishing, reliable event consumption, idempotency, and event patterns enable loose coupling and scalable architectures.

### 16.1-16.2 Event Processing Rules

Complete event processing guidance is available in:
- `rules/event-publishing.md` - Domain event patterns
- `rules/event-consuming.md` - Reliable event consumption

---

## 17. ImpEx Data Exchange

**Impact:** MEDIUM

Efficient data import and export patterns with streaming, validation, resumability, and delta processing enable reliable data integration.

### 17.1-17.2 ImpEx Rules

Complete ImpEx guidance is available in:
- `rules/impex-import-patterns.md` - Efficient import implementation
- `rules/impex-export-patterns.md` - Streaming export implementation

---

## 18. Search

**Impact:** HIGH

Solr search customization, query building, and faceting patterns ensure relevant search results and optimal performance.

### 18.1-18.2 Search Rules

Complete search guidance is available in:
- `rules/search-solr-customization.md` - Solr configuration and indexing
- `rules/search-query-building.md` - Safe query construction

---

## References

- [Intershop Knowledge Base](https://knowledge.intershop.com)
- [Intershop Support Portal](https://support.intershop.com)
- [Intershop PWA GitHub](https://github.com/intershop/intershop-pwa)
- [Intershop E-Commerce Platform](https://www.intershop.com/en/e-commerce-platform)
- [OWASP Security Guidelines](https://owasp.org)
- [SLF4J Documentation](https://www.slf4j.org/manual.html)
- [JSR-303 Bean Validation](https://beanvalidation.org/)
- [OpenTelemetry Tracing](https://opentelemetry.io/docs/concepts/signals/traces/)
