---
title: Authenticate REST Resources Like Server Actions
impact: CRITICAL
impactDescription: prevents unauthorized access to REST endpoints
tags: rest, security, authentication, authorization
---

## Authenticate REST Resources Like Server Actions

**Impact: CRITICAL (prevents unauthorized access to REST endpoints)**

All REST resources are publicly accessible endpoints. Authentication and authorization must be verified inside each resource method, not just at the middleware level.

**Incorrect (no authentication in resource):**

```java
// Bad: Unprotected REST resource
@Path("/orders")
public class OrderResource extends AbstractRestCollectionResource {

    @DELETE
    @Path("/{orderId}")
    public Response deleteOrder(@PathParam("orderId") String orderId) {
        // Anyone can call this! No auth check
        orderRepository.deleteOrder(orderId);
        return Response.ok().build();
    }

    @POST
    @Path("/{orderId}/submit")
    public Response submitOrder(@PathParam("orderId") String orderId) {
        // No verification of who is submitting
        orderService.submit(orderId);
        return Response.ok().build();
    }
}
```

**Correct (authentication inside each method):**

```java
@Path("/orders")
public class OrderResource extends AbstractRestCollectionResource {

    @Inject
    private AuthenticationService authService;

    @Inject
    private AuthorizationService authzService;

    @DELETE
    @Path("/{orderId}")
    public Response deleteOrder(@PathParam("orderId") String orderId) {
        // Step 1: Authenticate
        UserBO currentUser = authService.getCurrentUser();
        if (currentUser == null) {
            throw new WebApplicationException(Response.Status.UNAUTHORIZED);
        }

        // Step 2: Get resource
        OrderBO order = orderRepository.getOrder(orderId);
        if (order == null) {
            throw new WebApplicationException(Response.Status.NOT_FOUND);
        }

        // Step 3: Authorize
        if (!authzService.canDelete(currentUser, order)) {
            throw new WebApplicationException(Response.Status.FORBIDDEN);
        }

        // Step 4: Execute
        orderRepository.deleteOrder(orderId);
        return Response.ok().build();
    }

    @POST
    @Path("/{orderId}/submit")
    public Response submitOrder(@PathParam("orderId") String orderId, OrderSubmitRO submitData) {
        // Validate input first
        validateSubmitData(submitData);

        // Authenticate
        UserBO currentUser = authService.getCurrentUser();
        if (currentUser == null) {
            throw new WebApplicationException(Response.Status.UNAUTHORIZED);
        }

        // Get and verify ownership
        OrderBO order = orderRepository.getOrder(orderId);
        if (!order.getCustomer().equals(currentUser.getCustomer())) {
            throw new WebApplicationException(Response.Status.FORBIDDEN);
        }

        // Execute with audit
        orderService.submit(order, currentUser);

        return Response.ok().build();
    }
}
```

**Using ICM's token-based authentication:**

```java
@Path("/orders")
public class OrderResource extends AbstractRestCollectionResource {

    @Inject
    private TokenAuthenticationHandler tokenHandler;

    @GET
    @Path("/{orderId}")
    public Response getOrder(
            @PathParam("orderId") String orderId,
            @HeaderParam("Authorization") String authHeader) {

        // Validate bearer token
        TokenValidationResult tokenResult = tokenHandler.validateToken(authHeader);

        if (!tokenResult.isValid()) {
            return Response.status(Response.Status.UNAUTHORIZED)
                .entity(new ErrorRO("Invalid or expired token"))
                .build();
        }

        UserBO user = tokenResult.getUser();

        // Rest of the logic...
    }
}
```

**Authorization patterns:**

```java
// Role-based authorization
public class AuthorizationService {

    public boolean canDelete(UserBO user, OrderBO order) {
        // Admin can delete any order
        if (user.hasRole(Roles.ADMIN)) {
            return true;
        }

        // User can only delete their own draft orders
        if (user.hasRole(Roles.CUSTOMER)) {
            return order.getCustomer().equals(user.getCustomer())
                && order.getStatus() == OrderStatus.DRAFT;
        }

        return false;
    }

    public boolean canView(UserBO user, OrderBO order) {
        // Organization members can view organization orders
        return user.getOrganization().equals(order.getOrganization())
            || user.hasRole(Roles.ADMIN);
    }
}
```

**Security checklist for REST resources:**

| Step | Action | Example |
|------|--------|---------|
| 1 | Validate input | Schema validation, sanitization |
| 2 | Authenticate | Verify token/session |
| 3 | Load resource | Get entity from repository |
| 4 | Authorize | Check permissions |
| 5 | Execute | Perform business logic |
| 6 | Audit | Log sensitive operations |

Reference: [Guide - REST Style Guide](https://knowledge.intershop.com/kb/index.php/Display/25127U)
