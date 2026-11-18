---
title: Implement Customer-Specific Pricing Correctly
impact: CRITICAL
impactDescription: ensures accurate B2B pricing and contract compliance
tags: b2b, pricing, customer-specific, contracts, discounts
---

## Implement Customer-Specific Pricing Correctly

**Impact: CRITICAL (ensures accurate B2B pricing and contract compliance)**

B2B customers often have negotiated prices, volume discounts, and contract-specific pricing. Implementing this correctly is essential for B2B commerce.

**Incorrect (hardcoded pricing logic):**

```java
// Bad: Hardcoded discount logic without proper context
public class PricingPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        ProductBO product = dict.get("Product");
        CustomerBO customer = dict.get("Customer");

        Money basePrice = product.getBasePrice();

        // Hardcoded discount tiers - impossible to maintain!
        if ("GOLD".equals(customer.getTier())) {
            basePrice = basePrice.multiply(0.85);
        } else if ("SILVER".equals(customer.getTier())) {
            basePrice = basePrice.multiply(0.90);
        }

        // No audit trail, no contract validation
        dict.put("Price", basePrice);
        return PIPELET_NEXT;
    }
}
```

**Correct (extensible pricing service):**

```java
// 1. Define pricing context with all relevant information
public class B2BPricingContext {
    private final CustomerBO customer;
    private final OrganizationBO organization;
    private final ContractBO activeContract;
    private final BigDecimal quantity;
    private final Date priceDate;
    private final String channel;

    // Builder pattern for flexibility
    public static Builder builder() { return new Builder(); }
}

// 2. Pricing service with proper rule evaluation
public interface B2BPricingService {

    /**
     * Calculate price with full customer context.
     */
    PricingResult calculatePrice(ProductBO product, B2BPricingContext context);

    /**
     * Get all applicable price rules for debugging/transparency.
     */
    List<AppliedPriceRule> getAppliedRules(ProductBO product, B2BPricingContext context);
}

// 3. Implementation with rule priority
public class B2BPricingServiceImpl implements B2BPricingService {

    @Inject
    private ContractPriceRepository contractPriceRepository;

    @Inject
    private CustomerPriceRepository customerPriceRepository;

    @Inject
    private VolumePricingService volumePricingService;

    @Override
    public PricingResult calculatePrice(ProductBO product, B2BPricingContext context) {
        List<PriceRule> applicableRules = new ArrayList<>();
        Money finalPrice = product.getListPrice();

        // Priority 1: Contract-specific price (highest priority)
        if (context.getActiveContract() != null) {
            Optional<ContractPrice> contractPrice = contractPriceRepository
                .findPrice(product, context.getActiveContract());

            if (contractPrice.isPresent()) {
                finalPrice = contractPrice.get().getPrice();
                applicableRules.add(new ContractPriceRule(contractPrice.get()));
            }
        }

        // Priority 2: Customer-specific price
        if (applicableRules.isEmpty()) {
            Optional<CustomerPrice> customerPrice = customerPriceRepository
                .findPrice(product, context.getCustomer());

            if (customerPrice.isPresent()) {
                finalPrice = customerPrice.get().getPrice();
                applicableRules.add(new CustomerPriceRule(customerPrice.get()));
            }
        }

        // Priority 3: Volume/quantity discounts (can stack)
        VolumeDiscount volumeDiscount = volumePricingService
            .calculateDiscount(product, context.getQuantity());

        if (volumeDiscount.isApplicable()) {
            finalPrice = volumeDiscount.apply(finalPrice);
            applicableRules.add(new VolumeDiscountRule(volumeDiscount));
        }

        return PricingResult.builder()
            .finalPrice(finalPrice)
            .basePrice(product.getListPrice())
            .appliedRules(applicableRules)
            .priceValidUntil(calculateValidUntil(applicableRules))
            .build();
    }
}

// 4. Use in pipelet with proper context
public class B2BProductPricePipelet extends Pipelet {

    @Inject
    private B2BPricingService pricingService;

    @Override
    public int execute(PipelineDictionary dict) {
        ProductBO product = dict.get("Product");
        CustomerBO customer = dict.get("CurrentCustomer");
        BigDecimal quantity = dict.getOptional("Quantity", BigDecimal.ONE);

        B2BPricingContext context = B2BPricingContext.builder()
            .customer(customer)
            .organization(customer.getOrganization())
            .activeContract(customer.getActiveContract())
            .quantity(quantity)
            .priceDate(new Date())
            .channel(dict.get("Channel"))
            .build();

        PricingResult result = pricingService.calculatePrice(product, context);

        // Provide transparency to UI
        dict.put("Price", result.getFinalPrice());
        dict.put("BasePrice", result.getBasePrice());
        dict.put("AppliedDiscounts", result.getAppliedRules());
        dict.put("PriceValidUntil", result.getPriceValidUntil());

        return PIPELET_NEXT;
    }
}
```

**Price rule priority:**

| Priority | Rule Type | Description |
|----------|-----------|-------------|
| 1 | Contract Price | Negotiated fixed price |
| 2 | Customer Price | Customer-specific list |
| 3 | Organization Price | Organization-wide price |
| 4 | Volume Discount | Quantity-based |
| 5 | Tier Discount | Customer tier based |
| 6 | List Price | Default price |

Reference: [Intershop B2B Features](https://www.intershop.com/en/e-commerce-platform)
