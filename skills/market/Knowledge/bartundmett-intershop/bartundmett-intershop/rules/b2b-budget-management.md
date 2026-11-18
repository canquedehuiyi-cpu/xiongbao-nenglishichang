---
title: Implement Budget Management Correctly
impact: HIGH
impactDescription: enables proper B2B spending controls
tags: b2b, budget, spending, controls, procurement
---

## Implement Budget Management Correctly

**Impact: HIGH (enables proper B2B spending controls)**

B2B customers require budget controls at multiple levels: user, cost center, department, and organization. Implement atomic budget operations with proper validation and audit trails.

**Incorrect (unsafe budget handling):**

```java
// Bad: Non-atomic budget check and update
public class OrderService {

    public void placeOrder(OrderBO order) {
        UserBO user = order.getUser();
        Money orderTotal = order.getTotal();

        BudgetBO budget = budgetService.getBudget(user);

        if (budget.getRemaining().compareTo(orderTotal) >= 0) {
            // Race condition! Another order could be placed here
            budget.setSpent(budget.getSpent().add(orderTotal));
            budgetRepository.save(budget);

            orderRepository.save(order);
        }
    }
}

// Bad: No budget hierarchy consideration
public boolean checkBudget(UserBO user, Money amount) {
    BudgetBO userBudget = budgetService.getUserBudget(user);
    return userBudget.getRemaining().compareTo(amount) >= 0;
    // Ignores cost center and org-level budgets!
}

// Bad: No audit trail
public void updateBudget(String userId, Money newLimit) {
    BudgetBO budget = budgetRepository.findByUserId(userId);
    budget.setLimit(newLimit);  // No record of who changed it or why
    budgetRepository.save(budget);
}
```

**Correct (robust budget management):**

```java
// Good: Atomic budget reservation with pessimistic locking
@Injectable
public class BudgetService {

    @Inject
    private BudgetRepository budgetRepository;

    @Inject
    private BudgetAuditService auditService;

    @Transactional
    public BudgetReservation reserveBudget(UserBO user, Money amount, String orderId) {
        // Lock budget for update
        BudgetBO userBudget = budgetRepository.findByUserIdForUpdate(user.getId());

        // Check all budget levels
        BudgetCheckResult result = checkBudgetHierarchy(user, amount);

        if (!result.isApproved()) {
            return BudgetReservation.denied(result.getReason());
        }

        // Create atomic reservation
        BudgetReservation reservation = new BudgetReservation();
        reservation.setId(UUID.randomUUID().toString());
        reservation.setUserId(user.getId());
        reservation.setAmount(amount);
        reservation.setOrderId(orderId);
        reservation.setStatus(ReservationStatus.RESERVED);
        reservation.setExpiresAt(Instant.now().plus(Duration.ofHours(24)));

        // Reserve at all applicable levels
        reserveAtAllLevels(user, amount, reservation.getId());

        // Audit
        auditService.logReservation(reservation);

        return reservation;
    }

    @Transactional
    public void confirmReservation(String reservationId) {
        BudgetReservation reservation = reservationRepository.findById(reservationId);

        if (reservation.getStatus() != ReservationStatus.RESERVED) {
            throw new IllegalStateException("Reservation not in reserved state");
        }

        // Convert reservation to actual spend
        convertReservationToSpend(reservation);

        reservation.setStatus(ReservationStatus.CONFIRMED);
        reservation.setConfirmedAt(Instant.now());

        auditService.logConfirmation(reservation);
    }

    @Transactional
    public void releaseReservation(String reservationId, String reason) {
        BudgetReservation reservation = reservationRepository.findById(reservationId);

        // Release at all levels
        releaseAtAllLevels(reservation);

        reservation.setStatus(ReservationStatus.RELEASED);
        reservation.setReleaseReason(reason);

        auditService.logRelease(reservation);
    }
}

// Good: Hierarchical budget checking
@Injectable
public class BudgetHierarchyService {

    public BudgetCheckResult checkBudgetHierarchy(UserBO user, Money amount) {
        List<BudgetCheck> checks = new ArrayList<>();

        // 1. User personal budget
        BudgetBO userBudget = getBudget(user.getId(), BudgetType.USER);
        if (userBudget != null) {
            checks.add(checkSingleBudget(userBudget, amount, "User budget"));
        }

        // 2. Cost center budget
        CostCenterBO costCenter = user.getDefaultCostCenter();
        if (costCenter != null) {
            BudgetBO ccBudget = getBudget(costCenter.getId(), BudgetType.COST_CENTER);
            if (ccBudget != null) {
                checks.add(checkSingleBudget(ccBudget, amount, "Cost center budget"));
            }
        }

        // 3. Department budget
        DepartmentBO department = user.getDepartment();
        if (department != null) {
            BudgetBO deptBudget = getBudget(department.getId(), BudgetType.DEPARTMENT);
            if (deptBudget != null) {
                checks.add(checkSingleBudget(deptBudget, amount, "Department budget"));
            }
        }

        // 4. Organization budget
        OrganizationBO org = user.getOrganization();
        BudgetBO orgBudget = getBudget(org.getId(), BudgetType.ORGANIZATION);
        if (orgBudget != null) {
            checks.add(checkSingleBudget(orgBudget, amount, "Organization budget"));
        }

        // All must pass
        Optional<BudgetCheck> failed = checks.stream()
            .filter(c -> !c.isPassed())
            .findFirst();

        if (failed.isPresent()) {
            return BudgetCheckResult.denied(failed.get().getReason());
        }

        return BudgetCheckResult.approved(checks);
    }

    private BudgetCheck checkSingleBudget(BudgetBO budget, Money amount, String label) {
        Money available = budget.getLimit()
            .subtract(budget.getSpent())
            .subtract(budget.getReserved());

        if (available.compareTo(amount) < 0) {
            return BudgetCheck.failed(label,
                String.format("%s exceeded: available %s, requested %s",
                    label, available, amount));
        }

        return BudgetCheck.passed(label, available);
    }
}

// Good: Budget period management
@Injectable
public class BudgetPeriodService {

    public void resetBudgets(BudgetPeriod period) {
        List<BudgetBO> budgets = budgetRepository.findByPeriodType(period.getType());

        for (BudgetBO budget : budgets) {
            // Archive current period
            BudgetHistory history = new BudgetHistory();
            history.setBudgetId(budget.getId());
            history.setPeriod(period);
            history.setLimit(budget.getLimit());
            history.setSpent(budget.getSpent());
            history.setClosedAt(Instant.now());
            historyRepository.save(history);

            // Handle rollover
            if (budget.isRolloverEnabled()) {
                Money unused = budget.getLimit().subtract(budget.getSpent());
                Money rollover = unused.min(budget.getMaxRollover());
                budget.setLimit(budget.getBaseLimit().add(rollover));
            }

            // Reset spent
            budget.setSpent(Money.zero(budget.getCurrency()));
            budget.setReserved(Money.zero(budget.getCurrency()));
            budget.setPeriodStart(period.getStart());
            budget.setPeriodEnd(period.getEnd());

            budgetRepository.save(budget);

            auditService.logPeriodReset(budget, period);
        }
    }
}

// Good: Budget with comprehensive audit
@Injectable
public class BudgetAuditService {

    public void logBudgetChange(BudgetBO budget, BudgetChangeType type,
            Money oldValue, Money newValue, String userId, String reason) {

        BudgetAuditEntry entry = new BudgetAuditEntry();
        entry.setBudgetId(budget.getId());
        entry.setChangeType(type);
        entry.setOldValue(oldValue);
        entry.setNewValue(newValue);
        entry.setChangedBy(userId);
        entry.setReason(reason);
        entry.setTimestamp(Instant.now());
        entry.setIpAddress(RequestContext.getClientIP());

        auditRepository.save(entry);

        // Notify stakeholders for significant changes
        if (type == BudgetChangeType.LIMIT_INCREASED ||
            type == BudgetChangeType.LIMIT_DECREASED) {
            notifyBudgetOwners(budget, entry);
        }
    }
}
```

**Budget hierarchy levels:**

| Level | Scope | Typical Period | Override |
|-------|-------|----------------|----------|
| User | Individual | Monthly | No |
| Cost Center | Project/Team | Quarterly | By Manager |
| Department | Business Unit | Yearly | By Director |
| Organization | Company-wide | Yearly | By Admin |

Reference: [ICM Budget Management](https://knowledge.intershop.com/kb/index.php/Display/28Z610)
