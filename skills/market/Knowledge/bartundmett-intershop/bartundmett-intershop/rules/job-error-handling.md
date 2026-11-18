---
title: Handle Job Errors Properly
impact: MEDIUM
impactDescription: ensures reliable batch processing with recovery
tags: jobs, batch, error-handling, retry, recovery
---

## Handle Job Errors Properly

**Impact: MEDIUM (ensures reliable batch processing with recovery)**

Batch jobs must handle errors gracefully, supporting retry, partial completion, and proper notification of failures.

**Incorrect (poor error handling in jobs):**

```java
// Bad: No error handling - job fails completely on first error
public class ProductImportJob implements Job {

    @Override
    public void execute(JobExecutionContext context) {
        List<ProductData> products = readProductFile();

        for (ProductData data : products) {
            Product product = parseProduct(data);  // Could throw!
            productRepository.save(product);        // Could fail!
        }
    }
}

// Bad: Catching all exceptions silently
public void execute(JobExecutionContext context) {
    try {
        processProducts();
    } catch (Exception e) {
        // Swallowed! Job appears successful but isn't
    }
}

// Bad: No tracking of partial progress
public void execute(JobExecutionContext context) {
    for (ProductData data : products) {
        try {
            processProduct(data);
        } catch (Exception e) {
            logger.error("Error processing product");
            // No tracking of which products failed
        }
    }
}
```

**Correct (robust error handling):**

```java
// Good: Comprehensive error handling with tracking
@Injectable
public class ProductImportJob implements Job {

    @Inject
    private ProductService productService;

    @Inject
    private JobProgressService progressService;

    @Inject
    private NotificationService notificationService;

    @Override
    public void execute(JobExecutionContext context) {
        String jobId = context.getJobDetail().getKey().getName();
        JobResult result = new JobResult(jobId);

        List<ProductData> products = readProductFile();
        result.setTotalItems(products.size());

        progressService.initializeProgress(jobId, products.size());

        for (int i = 0; i < products.size(); i++) {
            ProductData data = products.get(i);

            try {
                processProduct(data);
                result.incrementSuccessful();

            } catch (ValidationException e) {
                // Validation error - skip item, don't retry
                result.addError(new ItemError(
                    i,
                    data.getSku(),
                    ErrorType.VALIDATION,
                    e.getMessage()
                ));
                logger.warn("Validation failed for SKU {}: {}",
                    data.getSku(), e.getMessage());

            } catch (RetryableException e) {
                // Transient error - retry with backoff
                boolean success = retryWithBackoff(data, 3);
                if (success) {
                    result.incrementSuccessful();
                } else {
                    result.addError(new ItemError(
                        i,
                        data.getSku(),
                        ErrorType.RETRYABLE,
                        "Failed after 3 retries: " + e.getMessage()
                    ));
                }

            } catch (Exception e) {
                // Unexpected error
                result.addError(new ItemError(
                    i,
                    data.getSku(),
                    ErrorType.UNEXPECTED,
                    e.getMessage()
                ));
                logger.error("Unexpected error processing SKU {}",
                    data.getSku(), e);
            }

            progressService.updateProgress(jobId, i + 1);

            // Check for cancellation
            if (context.getJobDetail().isCancelled()) {
                result.setCancelled(true);
                break;
            }
        }

        result.complete();
        saveResult(result);

        if (result.hasErrors()) {
            notificationService.sendJobErrorNotification(result);
        }
    }

    private boolean retryWithBackoff(ProductData data, int maxRetries) {
        int attempt = 0;
        while (attempt < maxRetries) {
            try {
                Thread.sleep((long) Math.pow(2, attempt) * 1000);
                processProduct(data);
                return true;
            } catch (RetryableException e) {
                attempt++;
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
        return false;
    }
}

// Good: Error categorization
public enum ErrorType {
    VALIDATION,      // Bad data, don't retry
    RETRYABLE,       // Transient error, can retry
    UNEXPECTED,      // Unknown error, needs investigation
    FATAL            // Stop job immediately
}

public class ItemError {
    private final int lineNumber;
    private final String identifier;
    private final ErrorType type;
    private final String message;
    private final Instant timestamp;
    private final String stackTrace;

    // Constructor, getters
}

// Good: Error thresholds for circuit breaking
@Injectable
public class ErrorThresholdHandler {

    private final AtomicInteger consecutiveErrors = new AtomicInteger(0);
    private static final int MAX_CONSECUTIVE_ERRORS = 10;
    private static final double MAX_ERROR_RATE = 0.5;

    public void recordSuccess() {
        consecutiveErrors.set(0);
    }

    public void recordError(JobResult result) throws JobAbortException {
        int consecutive = consecutiveErrors.incrementAndGet();

        // Too many consecutive errors
        if (consecutive >= MAX_CONSECUTIVE_ERRORS) {
            throw new JobAbortException(
                "Aborting job: " + consecutive + " consecutive errors");
        }

        // Overall error rate too high
        double errorRate = (double) result.getFailedCount() /
                          result.getProcessedCount();
        if (result.getProcessedCount() > 100 && errorRate > MAX_ERROR_RATE) {
            throw new JobAbortException(
                "Aborting job: Error rate " + (errorRate * 100) + "% exceeds threshold");
        }
    }
}

// Good: Error report generation
@Injectable
public class JobErrorReporter {

    public String generateErrorReport(JobResult result) {
        StringBuilder report = new StringBuilder();

        report.append("Job Execution Report\n");
        report.append("====================\n\n");
        report.append("Job ID: ").append(result.getJobId()).append("\n");
        report.append("Status: ").append(result.getStatus()).append("\n");
        report.append("Start: ").append(result.getStartTime()).append("\n");
        report.append("End: ").append(result.getEndTime()).append("\n");
        report.append("Duration: ").append(result.getDuration()).append("\n\n");

        report.append("Summary\n");
        report.append("-------\n");
        report.append("Total: ").append(result.getTotalItems()).append("\n");
        report.append("Successful: ").append(result.getSuccessfulCount()).append("\n");
        report.append("Failed: ").append(result.getFailedCount()).append("\n\n");

        if (result.hasErrors()) {
            report.append("Errors by Type\n");
            report.append("--------------\n");
            Map<ErrorType, Long> byType = result.getErrors().stream()
                .collect(groupingBy(ItemError::getType, counting()));
            byType.forEach((type, count) ->
                report.append(type).append(": ").append(count).append("\n"));

            report.append("\nError Details (first 50)\n");
            report.append("------------------------\n");
            result.getErrors().stream().limit(50).forEach(error ->
                report.append(String.format("Line %d [%s]: %s - %s\n",
                    error.getLineNumber(),
                    error.getType(),
                    error.getIdentifier(),
                    error.getMessage()))
            );
        }

        return report.toString();
    }
}

// Good: Dead letter queue for failed items
@Injectable
public class DeadLetterQueueService {

    @Inject
    private DeadLetterRepository repository;

    public void enqueue(String jobId, Object item, Exception error) {
        DeadLetterEntry entry = new DeadLetterEntry();
        entry.setJobId(jobId);
        entry.setPayload(serialize(item));
        entry.setErrorMessage(error.getMessage());
        entry.setStackTrace(ExceptionUtils.getStackTrace(error));
        entry.setCreatedAt(Instant.now());
        entry.setRetryCount(0);

        repository.save(entry);
    }

    public List<DeadLetterEntry> getForReprocessing(String jobId, int limit) {
        return repository.findByJobIdAndRetryCountLessThan(jobId, 3, limit);
    }

    public void markProcessed(String entryId) {
        repository.delete(entryId);
    }

    public void incrementRetryCount(String entryId) {
        DeadLetterEntry entry = repository.findById(entryId);
        entry.setRetryCount(entry.getRetryCount() + 1);
        entry.setLastRetryAt(Instant.now());
        repository.save(entry);
    }
}
```

**Error handling strategy:**

| Error Type | Action | Retry |
|------------|--------|-------|
| Validation | Log, skip item | No |
| Timeout | Retry with backoff | Yes (3x) |
| Connection | Retry with backoff | Yes (5x) |
| Rate limit | Wait and retry | Yes |
| Fatal | Abort job | No |

Reference: [ICM Job Framework](https://knowledge.intershop.com/kb/index.php/Display/2Y2945)
