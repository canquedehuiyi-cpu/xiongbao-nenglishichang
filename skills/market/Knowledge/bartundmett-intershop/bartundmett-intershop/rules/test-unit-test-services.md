---
title: Unit Test Services with Mocked Dependencies
impact: CRITICAL
impactDescription: enables reliable, fast tests that catch bugs early
tags: testing, unit-tests, mocking, mockito, services
---

## Unit Test Services with Mocked Dependencies

**Impact: CRITICAL (enables reliable, fast tests that catch bugs early)**

Services should be unit tested with all dependencies mocked. This isolates the unit under test and enables fast, deterministic tests.

**Incorrect (no mocking, relies on real dependencies):**

```java
// Bad: Integration test disguised as unit test
public class PricingServiceTest {

    private PricingService pricingService;

    @Before
    public void setup() {
        // Real dependencies - slow, flaky, hard to control
        pricingService = new PricingServiceImpl();
    }

    @Test
    public void testCalculatePrice() {
        // Relies on database state, external services
        ProductBO product = getProductFromDatabase("SKU123");
        Money price = pricingService.calculatePrice(product);
        assertNotNull(price);  // Weak assertion
    }
}
```

**Correct (properly mocked dependencies):**

```java
// Good: True unit test with mocked dependencies
public class PricingServiceTest {

    @Mock
    private ProductRepository productRepository;

    @Mock
    private DiscountService discountService;

    @Mock
    private TaxService taxService;

    @InjectMocks
    private PricingServiceImpl pricingService;

    @Before
    public void setup() {
        MockitoAnnotations.initMocks(this);
    }

    @Test
    public void testCalculatePrice_withDiscount_appliesDiscountBeforeTax() {
        // Arrange - set up controlled test data
        ProductBO product = createTestProduct("SKU123", Money.of(100, "EUR"));
        when(discountService.getDiscount(product)).thenReturn(Percentage.of(10));
        when(taxService.getTaxRate(product)).thenReturn(Percentage.of(19));

        // Act
        Money price = pricingService.calculatePrice(product);

        // Assert - specific, meaningful assertions
        assertEquals(Money.of(107.10, "EUR"), price);  // (100 - 10%) * 1.19

        // Verify interactions
        verify(discountService).getDiscount(product);
        verify(taxService).getTaxRate(product);
    }

    @Test
    public void testCalculatePrice_noDiscount_appliesOnlyTax() {
        ProductBO product = createTestProduct("SKU456", Money.of(50, "EUR"));
        when(discountService.getDiscount(product)).thenReturn(Percentage.ZERO);
        when(taxService.getTaxRate(product)).thenReturn(Percentage.of(19));

        Money price = pricingService.calculatePrice(product);

        assertEquals(Money.of(59.50, "EUR"), price);
    }

    private ProductBO createTestProduct(String sku, Money basePrice) {
        ProductBO product = mock(ProductBO.class);
        when(product.getSKU()).thenReturn(sku);
        when(product.getBasePrice()).thenReturn(basePrice);
        return product;
    }
}
```

**Test naming convention:**

```java
// Pattern: methodName_condition_expectedResult
@Test
public void calculatePrice_withExpiredDiscount_ignoresDiscount() { }

@Test
public void calculatePrice_withNullProduct_throwsIllegalArgumentException() { }

@Test
public void calculatePrice_withZeroQuantity_returnsZero() { }
```

**Key principles:**

| Principle | Description |
|-----------|-------------|
| Isolate | Mock all external dependencies |
| Arrange-Act-Assert | Clear test structure |
| One assertion focus | Test one behavior per test |
| Meaningful names | Describe scenario and expectation |
| Fast | Unit tests should run in milliseconds |

Reference: [Mockito Documentation](https://site.mockito.org/)
