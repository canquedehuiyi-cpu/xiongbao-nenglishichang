---
title: Implement Order Approval Workflows
impact: CRITICAL
impactDescription: enables B2B purchase controls and compliance
tags: b2b, approval, workflow, orders, compliance
---

## Implement Order Approval Workflows

**Impact: CRITICAL (enables B2B purchase controls and compliance)**

B2B orders often require approval based on value, product type, or buyer role. Implement flexible, auditable approval workflows.

**Incorrect (hardcoded approval logic):**

```java
// Bad: Hardcoded thresholds
public boolean needsApproval(OrderBO order) {
    return order.getTotal().isGreaterThan(Money.of(1000, "EUR"));
}

// Bad: No audit trail
public void approveOrder(String orderId, String approverId) {
    OrderBO order = orderRepository.getOrder(orderId);
    order.setStatus(OrderStatus.APPROVED);
    orderRepository.save(order);
}

// Bad: Single approver model
public UserBO getApprover(OrderBO order) {
    return order.getCreatedBy().getManager();
}
```

**Correct (flexible approval workflow):**

```java
// Good: Approval rule engine
@Injectable
public class ApprovalRuleEngine {

    @Inject
    private List<ApprovalRule> rules;

    public ApprovalRequirement evaluateOrder(OrderBO order, UserBO buyer) {
        ApprovalRequirement requirement = new ApprovalRequirement();

        for (ApprovalRule rule : rules) {
            if (rule.applies(order, buyer)) {
                ApprovalStep step = rule.getRequiredApproval(order, buyer);
                requirement.addStep(step);
            }
        }

        return requirement;
    }
}

// Good: Configurable approval rules
public interface ApprovalRule {
    boolean applies(OrderBO order, UserBO buyer);
    ApprovalStep getRequiredApproval(OrderBO order, UserBO buyer);
    int getPriority();
}

@Injectable
public class ValueBasedApprovalRule implements ApprovalRule {

    @Inject
    private ApprovalThresholdRepository thresholdRepo;

    @Override
    public boolean applies(OrderBO order, UserBO buyer) {
        // Check if order exceeds buyer's limit
        Money buyerLimit = getBuyerLimit(buyer);
        return order.getTotal().isGreaterThan(buyerLimit);
    }

    @Override
    public ApprovalStep getRequiredApproval(OrderBO order, UserBO buyer) {
        Money orderValue = order.getTotal();

        // Find appropriate approver based on value
        ApprovalThreshold threshold = thresholdRepo.findApplicable(
            buyer.getOrganization(), orderValue);

        return ApprovalStep.builder()
            .type(ApprovalType.VALUE_THRESHOLD)
            .approverRole(threshold.getRequiredRole())
            .approverLevel(threshold.getApprovalLevel())
            .reason("Order value " + orderValue + " exceeds limit")
            .build();
    }
}

@Injectable
public class RestrictedProductApprovalRule implements ApprovalRule {

    @Override
    public boolean applies(OrderBO order, UserBO buyer) {
        return order.getLineItems().stream()
            .anyMatch(item -> item.getProduct().isRestricted());
    }

    @Override
    public ApprovalStep getRequiredApproval(OrderBO order, UserBO buyer) {
        return ApprovalStep.builder()
            .type(ApprovalType.RESTRICTED_PRODUCT)
            .approverRole(Roles.PRODUCT_APPROVER)
            .reason("Order contains restricted products")
            .build();
    }
}

// Good: Approval workflow service with audit
@Injectable
public class ApprovalWorkflowService {

    @Inject
    private ApprovalRuleEngine ruleEngine;

    @Inject
    private AuditService auditService;

    @Inject
    private NotificationService notificationService;

    public void submitForApproval(OrderBO order, UserBO buyer) {
        ApprovalRequirement requirement = ruleEngine.evaluateOrder(order, buyer);

        if (requirement.isEmpty()) {
            // Auto-approve if no approval needed
            completeApproval(order, null, "Auto-approved - no approval required");
            return;
        }

        // Create approval request
        ApprovalRequest request = ApprovalRequest.builder()
            .order(order)
            .requester(buyer)
            .steps(requirement.getSteps())
            .createdAt(Instant.now())
            .status(ApprovalStatus.PENDING)
            .build();

        approvalRequestRepository.save(request);

        // Notify approvers
        for (ApprovalStep step : requirement.getSteps()) {
            List<UserBO> approvers = findApprovers(step, buyer.getOrganization());
            notificationService.notifyApprovers(request, approvers);
        }

        // Audit
        auditService.logApprovalSubmitted(order, buyer, requirement);
    }

    @Transactional
    public void approve(String requestId, UserBO approver, String comment) {
        ApprovalRequest request = approvalRequestRepository.get(requestId);

        // Validate approver has authority
        if (!canApprove(approver, request)) {
            throw new ForbiddenException("Not authorized to approve this request");
        }

        // Record approval
        ApprovalDecision decision = ApprovalDecision.builder()
            .approver(approver)
            .decision(Decision.APPROVED)
            .comment(comment)
            .timestamp(Instant.now())
            .build();

        request.addDecision(decision);

        // Check if all steps complete
        if (request.isFullyApproved()) {
            request.setStatus(ApprovalStatus.APPROVED);
            completeApproval(request.getOrder(), approver, "All approvals received");
        }

        approvalRequestRepository.save(request);

        // Audit
        auditService.logApprovalDecision(request, decision);
    }

    @Transactional
    public void reject(String requestId, UserBO approver, String reason) {
        ApprovalRequest request = approvalRequestRepository.get(requestId);

        // Record rejection
        ApprovalDecision decision = ApprovalDecision.builder()
            .approver(approver)
            .decision(Decision.REJECTED)
            .comment(reason)
            .timestamp(Instant.now())
            .build();

        request.addDecision(decision);
        request.setStatus(ApprovalStatus.REJECTED);

        approvalRequestRepository.save(request);

        // Notify requester
        notificationService.notifyRejection(request, reason);

        // Audit
        auditService.logApprovalDecision(request, decision);
    }
}
```

**Approval workflow states:**

```
DRAFT → PENDING_APPROVAL → APPROVED → SUBMITTED
                        ↘ REJECTED → (can edit and resubmit)
```

**Escalation handling:**

```java
// Good: Automatic escalation for stale approvals
@Scheduled(fixedRate = 3600000)  // Every hour
public void escalateStaleApprovals() {
    List<ApprovalRequest> stale = approvalRequestRepository
        .findPendingOlderThan(Duration.ofHours(24));

    for (ApprovalRequest request : stale) {
        // Find next level approver
        UserBO escalationApprover = findEscalationApprover(request);

        if (escalationApprover != null) {
            request.addStep(ApprovalStep.escalation(escalationApprover));
            notificationService.notifyEscalation(request, escalationApprover);
            auditService.logEscalation(request);
        }
    }
}
```

Reference: [Intershop B2B Approval Workflows](https://knowledge.intershop.com/kb/index.php/Display/29230E)
