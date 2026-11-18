---
title: Implement B2B User Roles and Permissions
impact: HIGH
impactDescription: enables proper access control for business users
tags: b2b, roles, permissions, rbac, authorization
---

## Implement B2B User Roles and Permissions

**Impact: HIGH (enables proper access control for business users)**

B2B applications require fine-grained role-based access control (RBAC) with inheritance, delegation, and organizational context. Implement flexible permission models that support complex enterprise hierarchies.

**Incorrect (hardcoded roles):**

```java
// Bad: Hardcoded role checks
public void approveOrder(String orderId, UserBO user) {
    if (user.getRole().equals("ADMIN") || user.getRole().equals("MANAGER")) {
        orderService.approve(orderId);
    }
    // No flexibility, no permission delegation
}

// Bad: Single role per user
public class UserBO {
    private String role;  // Only one role!

    public boolean isAdmin() {
        return "ADMIN".equals(role);
    }
}

// Bad: No organizational context
public boolean canAccessOrder(UserBO user, OrderBO order) {
    return user.hasPermission("VIEW_ORDERS");  // Ignores org structure
}
```

**Correct (flexible RBAC):**

```java
// Good: Permission-based authorization
@Injectable
public class PermissionService {

    @Inject
    private RoleRepository roleRepository;

    @Inject
    private PermissionRepository permissionRepository;

    public boolean hasPermission(UserBO user, String permission, Object context) {
        // Get all user's effective roles (direct + inherited)
        Set<RoleBO> effectiveRoles = getEffectiveRoles(user);

        // Check if any role grants the permission
        for (RoleBO role : effectiveRoles) {
            if (role.hasPermission(permission)) {
                // Check context-specific constraints
                if (checkContextConstraints(role, permission, context)) {
                    return true;
                }
            }
        }

        return false;
    }

    private Set<RoleBO> getEffectiveRoles(UserBO user) {
        Set<RoleBO> roles = new HashSet<>();

        // Direct roles
        roles.addAll(user.getRoles());

        // Roles from group membership
        for (UserGroupBO group : user.getGroups()) {
            roles.addAll(group.getRoles());
        }

        // Inherited roles from organization hierarchy
        OrganizationBO org = user.getOrganization();
        while (org != null) {
            roles.addAll(org.getDefaultRoles());
            org = org.getParent();
        }

        return roles;
    }

    private boolean checkContextConstraints(RoleBO role, String permission,
            Object context) {
        // Check if permission is scoped to specific context
        PermissionScopeBO scope = role.getPermissionScope(permission);

        if (scope == null || scope.isGlobal()) {
            return true;
        }

        if (context instanceof OrderBO) {
            return checkOrderScope(scope, (OrderBO) context);
        } else if (context instanceof ProductBO) {
            return checkProductScope(scope, (ProductBO) context);
        }

        return true;
    }
}

// Good: Role hierarchy with inheritance
@Injectable
public class RoleHierarchyService {

    public RoleBO createRole(RoleCreationData data) {
        RoleBO role = new RoleBO();
        role.setName(data.getName());
        role.setDescription(data.getDescription());

        // Inherit from parent role
        if (data.getParentRoleId() != null) {
            RoleBO parent = roleRepository.findById(data.getParentRoleId());
            role.setParentRole(parent);
            role.setInheritedPermissions(parent.getAllPermissions());
        }

        // Add direct permissions
        role.setDirectPermissions(data.getPermissions());

        return roleRepository.save(role);
    }

    public Set<PermissionBO> getEffectivePermissions(RoleBO role) {
        Set<PermissionBO> permissions = new HashSet<>(role.getDirectPermissions());

        // Add inherited permissions
        RoleBO parent = role.getParentRole();
        while (parent != null) {
            permissions.addAll(parent.getDirectPermissions());
            parent = parent.getParentRole();
        }

        return permissions;
    }
}

// Good: Context-aware permission checking
@Injectable
public class OrderAuthorizationService {

    @Inject
    private PermissionService permissionService;

    public boolean canViewOrder(UserBO user, OrderBO order) {
        // Global view permission
        if (permissionService.hasPermission(user, "orders.view.all", null)) {
            return true;
        }

        // Own orders
        if (order.getCreatedBy().equals(user.getId())) {
            return permissionService.hasPermission(user, "orders.view.own", null);
        }

        // Same organization
        if (isSameOrganization(user, order)) {
            return permissionService.hasPermission(user, "orders.view.organization", order);
        }

        // Subordinate's orders (for managers)
        if (isSubordinateOrder(user, order)) {
            return permissionService.hasPermission(user, "orders.view.subordinates", order);
        }

        return false;
    }

    public boolean canApproveOrder(UserBO user, OrderBO order) {
        // Must have approval permission
        if (!permissionService.hasPermission(user, "orders.approve", order)) {
            return false;
        }

        // Cannot approve own orders
        if (order.getCreatedBy().equals(user.getId())) {
            return false;
        }

        // Check approval limit
        Money userLimit = getApprovalLimit(user);
        if (order.getTotal().compareTo(userLimit) > 0) {
            return false;
        }

        // Check if user is in approval chain
        return isInApprovalChain(user, order);
    }
}

// Good: Role delegation
@Injectable
public class RoleDelegationService {

    @Transactional
    public DelegationBO delegateRole(DelegationRequest request) {
        UserBO delegator = request.getDelegator();
        UserBO delegate = request.getDelegate();
        RoleBO role = request.getRole();

        // Validate delegator has the role
        if (!delegator.hasRole(role)) {
            throw new AuthorizationException("Cannot delegate role you don't have");
        }

        // Check if role is delegatable
        if (!role.isDelegatable()) {
            throw new AuthorizationException("Role cannot be delegated");
        }

        // Check delegation depth
        if (exceedsDelegationDepth(delegator, role)) {
            throw new AuthorizationException("Delegation depth exceeded");
        }

        // Create delegation
        DelegationBO delegation = new DelegationBO();
        delegation.setDelegator(delegator);
        delegation.setDelegate(delegate);
        delegation.setRole(role);
        delegation.setStartDate(request.getStartDate());
        delegation.setEndDate(request.getEndDate());
        delegation.setReason(request.getReason());

        // Notify delegate
        notificationService.sendDelegationNotification(delegation);

        // Audit
        auditService.logDelegation(delegation);

        return delegationRepository.save(delegation);
    }

    @Scheduled(cron = "0 0 * * * *")
    public void cleanupExpiredDelegations() {
        List<DelegationBO> expired = delegationRepository
            .findExpiredDelegations(Instant.now());

        for (DelegationBO delegation : expired) {
            delegation.setStatus(DelegationStatus.EXPIRED);
            delegationRepository.save(delegation);

            notificationService.sendDelegationExpiredNotification(delegation);
        }
    }
}

// Good: Permission caching for performance
@Injectable
public class PermissionCacheService {

    private final Cache<String, Set<String>> permissionCache =
        CacheBuilder.newBuilder()
            .maximumSize(10000)
            .expireAfterWrite(Duration.ofMinutes(5))
            .build();

    public Set<String> getCachedPermissions(UserBO user) {
        String cacheKey = buildCacheKey(user);

        try {
            return permissionCache.get(cacheKey, () -> {
                return computeEffectivePermissions(user);
            });
        } catch (ExecutionException e) {
            return computeEffectivePermissions(user);
        }
    }

    public void invalidateCache(String userId) {
        // Invalidate on role changes
        permissionCache.invalidate(userId);
    }

    private String buildCacheKey(UserBO user) {
        return user.getId() + ":" + user.getOrganization().getId();
    }
}
```

**Standard B2B roles:**

| Role | Permissions | Scope |
|------|-------------|-------|
| Buyer | Create orders, View own | Personal |
| Approver | Approve orders up to limit | Organization |
| Purchasing Manager | Full order access, Manage buyers | Organization |
| Account Admin | Manage users, roles, budgets | Organization |
| Super Admin | Full access | Global |

Reference: [ICM User Management](https://knowledge.intershop.com/kb/index.php/Display/2Y4821)
