---
title: Implement Proper Access Control
impact: CRITICAL
impactDescription: prevents unauthorized access to resources and operations
tags: security, authorization, rbac, access-control, permissions
---

## Implement Proper Access Control

**Impact: CRITICAL (prevents unauthorized access to resources and operations)**

Enforce role-based access control (RBAC) at every layer. Never rely solely on UI hiding; always validate permissions server-side.

**Incorrect (broken access control):**

```java
// Bad: No authorization check
@DELETE
@Path("/orders/{orderId}")
public Response deleteOrder(@PathParam("orderId") String orderId) {
    // Anyone can delete any order!
    orderRepository.deleteOrder(orderId);
    return Response.ok().build();
}

// Bad: Only checks authentication, not authorization
@PUT
@Path("/users/{userId}/role")
public Response updateUserRole(@PathParam("userId") String userId, RoleUpdateRO request) {
    UserBO currentUser = authService.getCurrentUser();
    if (currentUser == null) {
        return Response.status(401).build();
    }
    // Authenticated but can any user change any role? No authorization!
    userService.updateRole(userId, request.getRole());
    return Response.ok().build();
}

// Bad: IDOR vulnerability - only checks if user is logged in
@GET
@Path("/invoices/{invoiceId}")
public InvoiceRO getInvoice(@PathParam("invoiceId") String invoiceId) {
    // Any logged-in user can access any invoice!
    return invoiceMapper.toRO(invoiceRepository.getInvoice(invoiceId));
}
```

**Correct (proper access control):**

```java
// Good: Full authorization check
@DELETE
@Path("/orders/{orderId}")
public Response deleteOrder(@PathParam("orderId") String orderId) {
    UserBO currentUser = authService.getCurrentUser();
    if (currentUser == null) {
        return Response.status(Response.Status.UNAUTHORIZED).build();
    }

    OrderBO order = orderRepository.getOrder(orderId);
    if (order == null) {
        return Response.status(Response.Status.NOT_FOUND).build();
    }

    // Check ownership OR admin role
    if (!authzService.canDeleteOrder(currentUser, order)) {
        return Response.status(Response.Status.FORBIDDEN).build();
    }

    orderRepository.deleteOrder(orderId);
    return Response.ok().build();
}

// Good: Authorization service with clear rules
@Injectable
public class AuthorizationService {

    public boolean canDeleteOrder(UserBO user, OrderBO order) {
        // Admins can delete any order
        if (user.hasRole(Roles.ORDER_ADMIN)) {
            return true;
        }

        // Users can only delete their own draft orders
        if (user.hasRole(Roles.CUSTOMER)) {
            return order.getCustomerId().equals(user.getCustomerId())
                && order.getStatus() == OrderStatus.DRAFT;
        }

        return false;
    }

    public boolean canAccessInvoice(UserBO user, InvoiceBO invoice) {
        // Finance team can access all invoices
        if (user.hasRole(Roles.FINANCE)) {
            return true;
        }

        // B2B: Organization members can access org invoices
        if (user.getOrganizationId() != null) {
            return invoice.getOrganizationId().equals(user.getOrganizationId());
        }

        // B2C: Only own invoices
        return invoice.getCustomerId().equals(user.getCustomerId());
    }

    public boolean canUpdateUserRole(UserBO currentUser, UserBO targetUser, Role newRole) {
        // Only admins can change roles
        if (!currentUser.hasRole(Roles.USER_ADMIN)) {
            return false;
        }

        // Cannot elevate to higher role than own
        if (newRole.getLevel() > currentUser.getHighestRoleLevel()) {
            return false;
        }

        // Cannot change own role (requires another admin)
        if (currentUser.getId().equals(targetUser.getId())) {
            return false;
        }

        return true;
    }
}

// Good: Resource-based access control annotation
@Target({ElementType.METHOD})
@Retention(RetentionPolicy.RUNTIME)
public @interface RequiresPermission {
    String resource();
    String action();
}

// Usage:
@GET
@Path("/invoices/{invoiceId}")
@RequiresPermission(resource = "invoice", action = "read")
public InvoiceRO getInvoice(@PathParam("invoiceId") String invoiceId) {
    UserBO currentUser = authService.getCurrentUser();
    InvoiceBO invoice = invoiceRepository.getInvoice(invoiceId);

    // Even with permission, verify ownership
    if (!authzService.canAccessInvoice(currentUser, invoice)) {
        throw new ForbiddenException("Not authorized to access this invoice");
    }

    return invoiceMapper.toRO(invoice);
}

// Good: Filtering lists by permission
@GET
@Path("/orders")
public List<OrderRO> getOrders() {
    UserBO currentUser = authService.getCurrentUser();

    // Only return orders user is allowed to see
    List<OrderBO> orders = orderRepository.findOrdersForUser(currentUser);

    return orderMapper.toRO(orders);
}
```

**B2B organization hierarchy:**

```java
// Good: B2B hierarchy-aware access control
public boolean canAccessB2BResource(UserBO user, B2BResource resource) {
    OrganizationBO userOrg = user.getOrganization();
    OrganizationBO resourceOrg = resource.getOrganization();

    // Same organization
    if (userOrg.getId().equals(resourceOrg.getId())) {
        return checkRolePermission(user, resource);
    }

    // Parent organization (headquarters)
    if (userOrg.isParentOf(resourceOrg)) {
        return user.hasRole(Roles.ORG_ADMIN);
    }

    return false;
}
```

**Access control matrix:**

| Role | Own Resources | Org Resources | All Resources |
|------|---------------|---------------|---------------|
| Customer | CRUD | - | - |
| Org User | CRUD | Read | - |
| Org Admin | CRUD | CRUD | - |
| Admin | CRUD | CRUD | CRUD |

Reference: [OWASP Access Control Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Access_Control_Cheat_Sheet.html)
