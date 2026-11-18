---
title: Use Guice Dependency Injection Correctly
impact: MEDIUM
impactDescription: enables testability and loose coupling
tags: guice, dependency-injection, ioc, testing, architecture
---

## Use Guice Dependency Injection Correctly

**Impact: MEDIUM (enables testability and loose coupling)**

ICM uses Google Guice for dependency injection. Proper use of Guice enables testable, loosely coupled components that can be easily replaced or mocked.

**Incorrect (static access and tight coupling):**

```java
// Bad: Static singleton access - untestable
public class OrderProcessor {

    public void processOrder(Order order) {
        // Static access to managers - can't mock for testing
        PricingMgr pricingMgr = NamingMgr.get(PricingMgr.class);
        InventoryMgr inventoryMgr = NamingMgr.get(InventoryMgr.class);
        EmailMgr emailMgr = NamingMgr.get(EmailMgr.class);

        Money price = pricingMgr.calculatePrice(order);
        inventoryMgr.reserveStock(order);
        emailMgr.sendConfirmation(order);
    }
}

// Bad: Constructor with concrete implementations
public class ProductService {
    private final ProductRepositoryImpl repository;  // Concrete class!

    public ProductService() {
        this.repository = new ProductRepositoryImpl();  // Direct instantiation!
    }
}
```

**Correct (proper dependency injection):**

```java
// Good: Field injection (Intershop's recommended style)
public class OrderProcessor {

    @Inject
    private PricingService pricingService;

    @Inject
    private InventoryService inventoryService;

    @Inject
    private NotificationService notificationService;

    public void processOrder(Order order) {
        // Dependencies are injected - easily mockable for testing
        Money price = pricingService.calculatePrice(order);
        inventoryService.reserveStock(order);
        notificationService.sendConfirmation(order);
    }
}

// Good: Constructor injection (alternative, more explicit)
public class ProductService {

    private final ProductRepository repository;

    @Inject
    public ProductService(ProductRepository repository) {  // Interface, not impl!
        this.repository = repository;
    }

    public ProductBO getProduct(String sku) {
        return repository.getProductBySKU(sku);
    }
}
```

**Guice module configuration:**

```java
// Define bindings in a Guice module
public class ProductModule extends AbstractModule {

    @Override
    protected void configure() {
        // Bind interface to implementation
        bind(ProductRepository.class).to(ProductRepositoryImpl.class);

        // Singleton scope for services
        bind(PricingService.class).to(PricingServiceImpl.class).in(Singleton.class);

        // Provider for complex instantiation
        bind(ExternalClient.class).toProvider(ExternalClientProvider.class);
    }

    // Provider method for objects needing configuration
    @Provides
    @Singleton
    public CacheManager provideCacheManager(CacheConfiguration config) {
        return new CacheManager(config);
    }
}

// Register module in objectgraph-local.properties
// local.modules=com.mycompany.product.internal.ProductModule
```

**Override bindings for customization:**

```java
// Custom project override module
public class CustomProductModule extends AbstractModule {

    @Override
    protected void configure() {
        // Override standard implementation with custom
        bind(PricingService.class).to(CustomPricingServiceImpl.class);
    }
}

// Register as override in objectgraph-local.properties
// local.overrideModules=com.mycompany.custom.CustomProductModule
```

**Testing with mocked dependencies:**

```java
public class OrderProcessorTest {

    @Mock
    private PricingService pricingService;

    @Mock
    private InventoryService inventoryService;

    @Mock
    private NotificationService notificationService;

    @InjectMocks
    private OrderProcessor orderProcessor;

    @Before
    public void setup() {
        MockitoAnnotations.initMocks(this);
    }

    @Test
    public void testProcessOrder() {
        Order order = createTestOrder();
        when(pricingService.calculatePrice(order)).thenReturn(Money.of(100, "USD"));

        orderProcessor.processOrder(order);

        verify(inventoryService).reserveStock(order);
        verify(notificationService).sendConfirmation(order);
    }
}
```

**Best practices:**

| Practice | Description |
|----------|-------------|
| Inject interfaces | Never inject concrete implementations |
| Field injection | Intershop's standard style |
| Module organization | One module per cartridge |
| Override modules | Use for customization, not base bindings |
| Avoid static access | Use injection instead of NamingMgr |
| Scope appropriately | Singleton for stateless services |

Reference: [Concept - Dependency Injection and ObjectGraphs](https://knowledge.intershop.com/kb/index.php/Display/Q23740)
