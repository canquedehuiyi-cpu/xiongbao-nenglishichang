---
title: Implement Proper Pipeline Error Handling
impact: MEDIUM
impactDescription: ensures graceful failure and user-friendly error messages
tags: pipelines, error-handling, transitions, recovery
---

## Implement Proper Pipeline Error Handling

**Impact: MEDIUM (ensures graceful failure and user-friendly error messages)**

Pipelines must handle errors gracefully with proper transitions, meaningful error messages, and recovery options.

**Incorrect (poor error handling):**

```xml
<%-- Bad: No error transitions --%>
<pipeline name="ProcessOrder" type="process">
    <node name="Start">
        <pipelet name="ValidateOrder"/>
        <pipelet name="ProcessPayment"/>
        <pipelet name="UpdateInventory"/>
        <pipelet name="SendConfirmation"/>
        <%-- If any fails, pipeline crashes with no recovery --%>
    </node>
</pipeline>
```

```java
// Bad: Swallowing errors in pipelet
public class ProcessPaymentPipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        try {
            paymentService.process(dict.get("Order"));
        } catch (Exception e) {
            // Error swallowed, no indication of failure!
            logger.error("Payment failed", e);
        }
        return PIPELET_NEXT;  // Continues as if successful
    }
}
```

**Correct (comprehensive error handling):**

```xml
<%-- Good: Pipeline with proper error transitions --%>
<pipeline name="ProcessOrder" type="process">

    <node name="Start">
        <pipelet name="ValidateOrderPipelet"/>
        <transition condition="valid" to="ProcessPayment"/>
        <transition condition="invalid" to="HandleValidationError"/>
    </node>

    <node name="ProcessPayment">
        <pipelet name="ProcessPaymentPipelet"/>
        <transition condition="success" to="UpdateInventory"/>
        <transition condition="declined" to="HandlePaymentDeclined"/>
        <transition condition="error" to="HandlePaymentError"/>
    </node>

    <node name="UpdateInventory">
        <pipelet name="UpdateInventoryPipelet"/>
        <transition condition="success" to="SendConfirmation"/>
        <transition condition="insufficient" to="HandleInsufficientStock"/>
        <transition condition="error" to="HandleInventoryError"/>
    </node>

    <node name="SendConfirmation">
        <pipelet name="SendConfirmationPipelet"/>
        <transition condition="success" to="Success"/>
        <transition condition="error" to="LogNotificationFailure"/>
        <%-- Notification failure is non-critical --%>
    </node>

    <node name="LogNotificationFailure">
        <pipelet name="LogNotificationFailurePipelet"/>
        <transition to="Success"/>
        <%-- Continue to success, will retry notification later --%>
    </node>

    <%-- Error handling nodes --%>
    <node name="HandleValidationError">
        <pipelet name="SetErrorResponsePipelet">
            <param name="ErrorCode" value="VALIDATION_ERROR"/>
            <param name="ErrorTemplate" value="error/ValidationError"/>
        </pipelet>
        <transition to="Error"/>
    </node>

    <node name="HandlePaymentDeclined">
        <pipelet name="SetErrorResponsePipelet">
            <param name="ErrorCode" value="PAYMENT_DECLINED"/>
            <param name="ErrorTemplate" value="error/PaymentDeclined"/>
        </pipelet>
        <pipelet name="RollbackOrderPipelet"/>
        <transition to="Error"/>
    </node>

    <node name="HandlePaymentError">
        <pipelet name="SetErrorResponsePipelet">
            <param name="ErrorCode" value="PAYMENT_ERROR"/>
            <param name="ErrorTemplate" value="error/PaymentError"/>
        </pipelet>
        <pipelet name="SchedulePaymentRetryPipelet"/>
        <transition to="Error"/>
    </node>

    <node name="HandleInsufficientStock">
        <pipelet name="ReversePaymentPipelet"/>
        <pipelet name="SetErrorResponsePipelet">
            <param name="ErrorCode" value="INSUFFICIENT_STOCK"/>
            <param name="ErrorTemplate" value="error/InsufficientStock"/>
        </pipelet>
        <transition to="Error"/>
    </node>

    <node name="Success">
        <return status="success"/>
    </node>

    <node name="Error">
        <return status="error"/>
    </node>

</pipeline>
```

**Pipelet with proper exit conditions:**

```java
// Good: Pipelet with multiple exit conditions
public class ProcessPaymentPipelet extends Pipelet {

    public static final int PIPELET_SUCCESS = 1;
    public static final int PIPELET_DECLINED = 2;
    public static final int PIPELET_ERROR = 3;

    @Inject
    private PaymentService paymentService;

    @Override
    public int execute(PipelineDictionary dict) {
        OrderBO order = dict.getRequired("Order");

        try {
            PaymentResult result = paymentService.process(order);

            if (result.isSuccess()) {
                dict.put("PaymentTransactionId", result.getTransactionId());
                dict.put("PaymentConfirmation", result.getConfirmation());
                return PIPELET_SUCCESS;
            }

            if (result.isDeclined()) {
                dict.put("DeclineReason", result.getDeclineReason());
                dict.put("DeclineCode", result.getDeclineCode());
                logger.info("Payment declined",
                    kv("orderId", order.getId()),
                    kv("reason", result.getDeclineReason()));
                return PIPELET_DECLINED;
            }

            // Unexpected result
            dict.put("ErrorMessage", "Unexpected payment result: " + result.getStatus());
            return PIPELET_ERROR;

        } catch (PaymentGatewayException e) {
            logger.error("Payment gateway error",
                kv("orderId", order.getId()),
                kv("gateway", e.getGateway()),
                e);
            dict.put("ErrorMessage", "Payment service temporarily unavailable");
            dict.put("ErrorCode", "GATEWAY_ERROR");
            dict.put("RetryAfter", calculateRetryDelay(e));
            return PIPELET_ERROR;

        } catch (Exception e) {
            logger.error("Unexpected payment error",
                kv("orderId", order.getId()), e);
            dict.put("ErrorMessage", "An unexpected error occurred");
            dict.put("ErrorCode", "INTERNAL_ERROR");
            return PIPELET_ERROR;
        }
    }

    @Override
    protected void createConnectors() {
        createResultConnector("success", PIPELET_SUCCESS);
        createResultConnector("declined", PIPELET_DECLINED);
        createResultConnector("error", PIPELET_ERROR);
    }
}
```

**Error response pipelet:**

```java
// Good: Standardized error response
public class SetErrorResponsePipelet extends Pipelet {

    @Override
    public int execute(PipelineDictionary dict) {
        String errorCode = getParameter("ErrorCode");
        String errorTemplate = getParameter("ErrorTemplate");

        // Build user-friendly error
        ErrorResponse error = new ErrorResponse();
        error.setCode(errorCode);
        error.setMessage(getLocalizedMessage(errorCode, dict.get("CurrentLocale")));
        error.setDetails(dict.getOptional("ErrorMessage", ""));
        error.setCorrelationId(MDC.get("correlationId"));

        dict.put("ErrorResponse", error);
        dict.put("ErrorTemplate", errorTemplate);

        // Log for monitoring
        logger.warn("Order processing error",
            kv("errorCode", errorCode),
            kv("orderId", dict.getOptional("OrderId", "unknown")));

        return PIPELET_NEXT;
    }
}
```

**Error handling patterns:**

| Error Type | Handle | Recovery |
|------------|--------|----------|
| Validation | Show form errors | User corrects input |
| Payment declined | Show decline reason | User uses different payment |
| Gateway error | Retry with backoff | Auto-retry or user retry |
| Inventory | Rollback payment | Notify user, suggest alternatives |
| Notification | Log and continue | Async retry |

Reference: [Guide - Pipeline Development](https://knowledge.intershop.com/kb/index.php/Display/24Y887)
