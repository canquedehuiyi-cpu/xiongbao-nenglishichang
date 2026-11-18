---
title: Implement Quote Management Correctly
impact: HIGH
impactDescription: enables proper B2B quotation workflows
tags: b2b, quote, rfq, negotiation, pricing
---

## Implement Quote Management Correctly

**Impact: HIGH (enables proper B2B quotation workflows)**

B2B quote management requires proper state machine implementation, version control, and integration with approval workflows for negotiated pricing.

**Incorrect (simplified quote handling):**

```java
// Bad: No state validation
public class QuoteService {

    public void submitQuote(String quoteId, Money price) {
        QuoteBO quote = quoteRepository.findById(quoteId);
        quote.setPrice(price);
        quote.setStatus("SUBMITTED");
        quoteRepository.save(quote);  // No validation of state transition!
    }

    public void acceptQuote(String quoteId) {
        QuoteBO quote = quoteRepository.findById(quoteId);
        quote.setStatus("ACCEPTED");  // What if it was already rejected?
        quoteRepository.save(quote);
    }
}

// Bad: No version history
public void updateQuote(String quoteId, QuoteUpdateData data) {
    QuoteBO quote = quoteRepository.findById(quoteId);
    quote.setPrice(data.getPrice());  // Previous price lost!
    quote.setItems(data.getItems());
    quoteRepository.save(quote);
}

// Bad: No expiration handling
public OrderBO convertQuoteToOrder(String quoteId) {
    QuoteBO quote = quoteRepository.findById(quoteId);
    return orderService.createFromQuote(quote);  // Quote might be expired!
}
```

**Correct (robust quote management):**

```java
// Good: State machine for quote lifecycle
public enum QuoteStatus {
    DRAFT,
    SUBMITTED,
    IN_REVIEW,
    COUNTER_OFFERED,
    ACCEPTED,
    REJECTED,
    EXPIRED,
    CONVERTED;

    private static final Map<QuoteStatus, Set<QuoteStatus>> TRANSITIONS = Map.of(
        DRAFT, Set.of(SUBMITTED, EXPIRED),
        SUBMITTED, Set.of(IN_REVIEW, REJECTED, EXPIRED),
        IN_REVIEW, Set.of(ACCEPTED, REJECTED, COUNTER_OFFERED, EXPIRED),
        COUNTER_OFFERED, Set.of(ACCEPTED, REJECTED, COUNTER_OFFERED, EXPIRED),
        ACCEPTED, Set.of(CONVERTED, EXPIRED)
    );

    public boolean canTransitionTo(QuoteStatus target) {
        Set<QuoteStatus> allowed = TRANSITIONS.get(this);
        return allowed != null && allowed.contains(target);
    }
}

@Injectable
public class QuoteStateMachine {

    @Inject
    private QuoteRepository quoteRepository;

    @Inject
    private QuoteAuditService auditService;

    @Transactional
    public QuoteBO transition(String quoteId, QuoteStatus newStatus,
            String userId, String reason) {

        QuoteBO quote = quoteRepository.findByIdForUpdate(quoteId);
        QuoteStatus currentStatus = quote.getStatus();

        if (!currentStatus.canTransitionTo(newStatus)) {
            throw new InvalidStateTransitionException(
                String.format("Cannot transition from %s to %s",
                    currentStatus, newStatus));
        }

        quote.setStatus(newStatus);
        quote.setLastModifiedBy(userId);
        quote.setLastModifiedAt(Instant.now());

        auditService.logTransition(quote, currentStatus, newStatus, userId, reason);

        return quoteRepository.save(quote);
    }
}

// Good: Version control for quotes
@Injectable
public class QuoteVersionService {

    @Inject
    private QuoteVersionRepository versionRepository;

    @Transactional
    public QuoteVersionBO createVersion(QuoteBO quote, String userId, String comment) {
        // Archive current state
        QuoteVersionBO version = new QuoteVersionBO();
        version.setQuoteId(quote.getId());
        version.setVersionNumber(quote.getCurrentVersion() + 1);
        version.setCreatedBy(userId);
        version.setCreatedAt(Instant.now());
        version.setComment(comment);

        // Snapshot all quote data
        version.setSnapshot(createSnapshot(quote));

        versionRepository.save(version);

        // Update quote version number
        quote.setCurrentVersion(version.getVersionNumber());

        return version;
    }

    private QuoteSnapshot createSnapshot(QuoteBO quote) {
        QuoteSnapshot snapshot = new QuoteSnapshot();
        snapshot.setItems(quote.getItems().stream()
            .map(this::snapshotItem)
            .collect(toList()));
        snapshot.setSubtotal(quote.getSubtotal());
        snapshot.setDiscount(quote.getDiscount());
        snapshot.setTotal(quote.getTotal());
        snapshot.setTerms(quote.getTerms());
        snapshot.setValidUntil(quote.getValidUntil());
        return snapshot;
    }

    public List<QuoteVersionBO> getVersionHistory(String quoteId) {
        return versionRepository.findByQuoteIdOrderByVersionDesc(quoteId);
    }

    public QuoteVersionBO compareVersions(String quoteId, int v1, int v2) {
        QuoteVersionBO version1 = versionRepository.findByQuoteIdAndVersion(quoteId, v1);
        QuoteVersionBO version2 = versionRepository.findByQuoteIdAndVersion(quoteId, v2);

        return createDiff(version1, version2);
    }
}

// Good: Counter-offer handling
@Injectable
public class QuoteNegotiationService {

    @Inject
    private QuoteStateMachine stateMachine;

    @Inject
    private QuoteVersionService versionService;

    @Inject
    private NotificationService notificationService;

    @Transactional
    public QuoteBO submitCounterOffer(String quoteId, CounterOfferData data,
            String userId) {

        QuoteBO quote = quoteRepository.findById(quoteId);

        // Validate counter offer
        validateCounterOffer(quote, data);

        // Create version before changes
        versionService.createVersion(quote, userId,
            "Counter offer from " + (data.isFromBuyer() ? "buyer" : "seller"));

        // Apply counter offer
        if (data.getPriceAdjustments() != null) {
            applyPriceAdjustments(quote, data.getPriceAdjustments());
        }
        if (data.getQuantityChanges() != null) {
            applyQuantityChanges(quote, data.getQuantityChanges());
        }
        if (data.getNewValidUntil() != null) {
            quote.setValidUntil(data.getNewValidUntil());
        }

        quote.setNegotiationNotes(data.getNotes());
        quote.setCounterOfferCount(quote.getCounterOfferCount() + 1);

        // Transition state
        stateMachine.transition(quoteId, QuoteStatus.COUNTER_OFFERED,
            userId, "Counter offer submitted");

        // Notify other party
        notifyCounterOffer(quote, data.isFromBuyer());

        return quote;
    }
}

// Good: Expiration handling
@Injectable
public class QuoteExpirationService {

    @Scheduled(cron = "0 0 * * * *")  // Every hour
    @Transactional
    public void processExpiredQuotes() {
        Instant now = Instant.now();
        List<QuoteBO> expiring = quoteRepository.findExpiringQuotes(now);

        for (QuoteBO quote : expiring) {
            try {
                stateMachine.transition(quote.getId(), QuoteStatus.EXPIRED,
                    "SYSTEM", "Quote validity period ended");

                notificationService.sendQuoteExpiredNotification(quote);

            } catch (Exception e) {
                logger.error("Failed to expire quote {}", quote.getId(), e);
            }
        }
    }

    public void extendValidity(String quoteId, Instant newValidUntil, String userId) {
        QuoteBO quote = quoteRepository.findById(quoteId);

        if (quote.getStatus() == QuoteStatus.EXPIRED) {
            throw new QuoteException("Cannot extend expired quote");
        }

        if (newValidUntil.isBefore(quote.getValidUntil())) {
            throw new QuoteException("New validity must be after current");
        }

        versionService.createVersion(quote, userId, "Validity extended");

        quote.setValidUntil(newValidUntil);
        quote.setExtensionCount(quote.getExtensionCount() + 1);

        auditService.logValidityExtension(quote, newValidUntil, userId);
    }
}

// Good: Quote to order conversion with validation
@Injectable
public class QuoteConversionService {

    @Transactional
    public OrderBO convertToOrder(String quoteId, String userId) {
        QuoteBO quote = quoteRepository.findByIdForUpdate(quoteId);

        // Validate quote is convertible
        validateForConversion(quote);

        // Check quote hasn't expired
        if (Instant.now().isAfter(quote.getValidUntil())) {
            throw new QuoteExpiredException("Quote has expired");
        }

        // Verify pricing still valid
        verifyPricing(quote);

        // Create order
        OrderBO order = orderService.createOrder(
            quote.getCustomer(),
            convertItems(quote.getItems()),
            quote.getShippingAddress(),
            quote.getBillingAddress()
        );

        // Apply negotiated pricing
        order.setQuoteId(quoteId);
        order.setNegotiatedPricing(true);

        // Transition quote
        stateMachine.transition(quoteId, QuoteStatus.CONVERTED,
            userId, "Converted to order " + order.getOrderNumber());

        // Link quote and order
        quote.setConvertedOrderId(order.getId());

        return order;
    }

    private void validateForConversion(QuoteBO quote) {
        if (quote.getStatus() != QuoteStatus.ACCEPTED) {
            throw new QuoteException("Only accepted quotes can be converted");
        }

        if (quote.getItems().isEmpty()) {
            throw new QuoteException("Quote has no items");
        }
    }
}
```

**Quote status workflow:**

| Status | Buyer Actions | Seller Actions |
|--------|---------------|----------------|
| DRAFT | Submit, Delete | - |
| SUBMITTED | - | Review, Reject |
| IN_REVIEW | - | Accept, Counter, Reject |
| COUNTER_OFFERED | Accept, Counter, Reject | Accept, Counter |
| ACCEPTED | Convert to Order | - |
| REJECTED | Request New Quote | - |
| EXPIRED | Request Extension | - |

Reference: [ICM Quote Management](https://knowledge.intershop.com/kb/index.php/Display/2X2731)
