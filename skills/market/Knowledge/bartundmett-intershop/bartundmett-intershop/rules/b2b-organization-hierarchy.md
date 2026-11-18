---
title: Implement Organization Hierarchy Correctly
impact: CRITICAL
impactDescription: enables proper B2B customer structure and permissions
tags: b2b, organization, hierarchy, permissions, structure
---

## Implement Organization Hierarchy Correctly

**Impact: CRITICAL (enables proper B2B customer structure and permissions)**

B2B organizations have complex hierarchies with departments, cost centers, and approval chains. Implement proper traversal and permission inheritance.

**Incorrect (flat organization handling):**

```java
// Bad: Ignoring organization hierarchy
public List<OrderBO> getOrders(UserBO user) {
    // Only gets user's direct orders, ignores org structure
    return orderRepository.findByUserId(user.getId());
}

// Bad: No permission inheritance
public boolean canApproveOrder(UserBO user, OrderBO order) {
    // Only checks direct assignment
    return order.getAssignedApproverId().equals(user.getId());
}

// Bad: Flat budget checking
public boolean hasBudget(UserBO user, Money amount) {
    BudgetBO budget = budgetRepository.findByUserId(user.getId());
    return budget.getRemaining().isGreaterThan(amount);
}
```

**Correct (hierarchy-aware implementation):**

```java
// Good: Organization structure model
public interface OrganizationBO {
    String getId();
    String getName();
    OrganizationBO getParent();
    List<OrganizationBO> getChildren();
    OrganizationType getType();  // COMPANY, DIVISION, DEPARTMENT, COST_CENTER

    // Hierarchy traversal
    List<OrganizationBO> getAncestors();
    List<OrganizationBO> getDescendants();
    boolean isAncestorOf(OrganizationBO other);
    boolean isDescendantOf(OrganizationBO other);
}

// Good: Organization service with hierarchy support
@Injectable
public class OrganizationService {

    public List<OrganizationBO> getVisibleOrganizations(UserBO user) {
        OrganizationBO userOrg = user.getOrganization();

        // User can see their org and all descendants
        List<OrganizationBO> visible = new ArrayList<>();
        visible.add(userOrg);
        visible.addAll(userOrg.getDescendants());

        // Org admins can also see parent orgs
        if (user.hasRole(Roles.ORG_ADMIN)) {
            visible.addAll(userOrg.getAncestors());
        }

        return visible;
    }

    public boolean canManageOrganization(UserBO user, OrganizationBO targetOrg) {
        OrganizationBO userOrg = user.getOrganization();

        // Must be admin
        if (!user.hasRole(Roles.ORG_ADMIN)) {
            return false;
        }

        // Can manage own org and descendants
        return userOrg.equals(targetOrg) || userOrg.isAncestorOf(targetOrg);
    }
}

// Good: Hierarchy-aware order access
public class B2BOrderService {

    @Inject
    private OrganizationService orgService;

    public List<OrderBO> getAccessibleOrders(UserBO user) {
        Set<String> visibleOrgIds = orgService.getVisibleOrganizations(user)
            .stream()
            .map(OrganizationBO::getId)
            .collect(Collectors.toSet());

        return orderRepository.findByOrganizationIds(visibleOrgIds);
    }

    public boolean canViewOrder(UserBO user, OrderBO order) {
        // Own orders always visible
        if (order.getCreatedBy().equals(user.getId())) {
            return true;
        }

        // Check organization visibility
        OrganizationBO orderOrg = order.getOrganization();
        return orgService.getVisibleOrganizations(user).contains(orderOrg);
    }
}

// Good: Budget with hierarchy inheritance
public class B2BBudgetService {

    public BudgetCheckResult checkBudget(UserBO user, Money amount) {
        // Check personal budget first
        BudgetBO personalBudget = budgetRepository.findByUserId(user.getId());
        if (personalBudget != null && personalBudget.hasRemaining(amount)) {
            return BudgetCheckResult.approved(personalBudget);
        }

        // Check cost center budget
        OrganizationBO costCenter = user.getCostCenter();
        if (costCenter != null) {
            BudgetBO costCenterBudget = budgetRepository.findByOrgId(costCenter.getId());
            if (costCenterBudget != null && costCenterBudget.hasRemaining(amount)) {
                return BudgetCheckResult.approved(costCenterBudget);
            }
        }

        // Check department budget
        OrganizationBO department = user.getDepartment();
        if (department != null) {
            BudgetBO deptBudget = budgetRepository.findByOrgId(department.getId());
            if (deptBudget != null && deptBudget.hasRemaining(amount)) {
                return BudgetCheckResult.approved(deptBudget);
            }
        }

        // No budget available - requires approval
        return BudgetCheckResult.requiresApproval(findApprover(user, amount));
    }

    private UserBO findApprover(UserBO user, Money amount) {
        // Walk up hierarchy to find approver with sufficient limit
        OrganizationBO org = user.getOrganization();

        while (org != null) {
            UserBO approver = org.getApprover();
            if (approver != null && approver.getApprovalLimit().isGreaterThan(amount)) {
                return approver;
            }
            org = org.getParent();
        }

        return null;  // No approver found, escalate to admin
    }
}
```

**Efficient hierarchy queries:**

```java
// Good: Materialized path for efficient ancestor/descendant queries
@Entity
public class OrganizationPO {

    @Column(name = "PATH")
    private String path;  // e.g., "/1/5/12/45/"

    @Column(name = "DEPTH")
    private int depth;

    public List<OrganizationPO> findDescendants() {
        // Efficient LIKE query on path
        return query("FROM OrganizationPO o WHERE o.path LIKE :pathPrefix",
            Map.of("pathPrefix", this.path + "%"));
    }

    public List<OrganizationPO> findAncestors() {
        // Extract IDs from path
        List<String> ancestorIds = extractIdsFromPath(this.path);
        return query("FROM OrganizationPO o WHERE o.id IN :ids",
            Map.of("ids", ancestorIds));
    }
}
```

**Hierarchy pattern summary:**

| Requirement | Pattern |
|-------------|---------|
| Find children | Direct parent reference |
| Find all descendants | Materialized path + LIKE |
| Find ancestors | Parse path or recursive query |
| Permission inheritance | Walk up hierarchy |
| Budget rollup | Aggregate down hierarchy |

Reference: [Intershop B2B Organization Management](https://knowledge.intershop.com/kb/index.php/Display/29230E)
