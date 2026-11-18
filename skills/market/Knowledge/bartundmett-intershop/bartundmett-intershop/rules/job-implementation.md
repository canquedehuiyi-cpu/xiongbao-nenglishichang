---
title: Implement Scheduled Jobs Correctly
impact: MEDIUM
impactDescription: ensures reliable background processing
tags: jobs, scheduling, background, processing
---

## Implement Scheduled Jobs Correctly

**Impact: MEDIUM (ensures reliable background processing)**

Scheduled jobs handle background tasks like imports, cleanups, and synchronizations. Implement them with proper error handling, progress tracking, and graceful shutdown.

**Incorrect (fragile job implementation):**

```java
// Bad: No error handling, no progress, no graceful shutdown
public class ProductSyncJob implements Job {

    @Override
    public void execute(JobContext context) {
        List<Product> products = externalService.getAllProducts();

        for (Product product : products) {
            productService.syncProduct(product);  // Fails silently
        }
        // No indication of success or failure
    }
}

// Bad: Long-running without checkpoints
public class DataCleanupJob implements Job {

    @Override
    public void execute(JobContext context) {
        // Runs for hours, if interrupted all progress lost
        while (hasMoreData()) {
            cleanupNextBatch();
        }
    }
}
```

**Correct (robust job implementation):**

```java
// Good: Well-structured job with full observability
public class ProductSyncJob implements Job {

    private static final Logger logger = LoggerFactory.getLogger(ProductSyncJob.class);

    @Inject
    private ProductService productService;

    @Inject
    private ExternalCatalogService catalogService;

    @Inject
    private JobProgressService progressService;

    @Override
    public void execute(JobContext context) {
        String jobId = context.getJobId();

        logger.info("Starting product sync job", kv("jobId", jobId));

        try {
            // Initialize progress tracking
            List<String> productIds = catalogService.getProductIdsToSync();
            progressService.initialize(jobId, productIds.size());

            int successCount = 0;
            int errorCount = 0;
            List<SyncError> errors = new ArrayList<>();

            for (int i = 0; i < productIds.size(); i++) {
                // Check for cancellation
                if (context.isCancelled()) {
                    logger.info("Job cancelled by user",
                        kv("jobId", jobId),
                        kv("processed", i));
                    progressService.setCancelled(jobId);
                    return;
                }

                String productId = productIds.get(i);

                try {
                    ProductData data = catalogService.getProduct(productId);
                    productService.syncProduct(data);
                    successCount++;
                } catch (Exception e) {
                    errorCount++;
                    errors.add(new SyncError(productId, e.getMessage()));
                    logger.warn("Failed to sync product",
                        kv("productId", productId),
                        kv("error", e.getMessage()));
                }

                // Update progress periodically
                if (i % 100 == 0) {
                    progressService.updateProgress(jobId, i + 1, successCount, errorCount);
                }
            }

            // Job completed
            JobResult result = JobResult.builder()
                .totalProcessed(productIds.size())
                .successCount(successCount)
                .errorCount(errorCount)
                .errors(errors)
                .build();

            progressService.setCompleted(jobId, result);

            logger.info("Product sync job completed",
                kv("jobId", jobId),
                kv("success", successCount),
                kv("errors", errorCount));

        } catch (Exception e) {
            logger.error("Product sync job failed", kv("jobId", jobId), e);
            progressService.setFailed(jobId, e.getMessage());
            throw e;
        }
    }
}

// Good: Restartable job with checkpoints
public class LargeDataMigrationJob implements Job {

    @Inject
    private JobCheckpointService checkpointService;

    @Override
    public void execute(JobContext context) {
        String jobId = context.getJobId();

        // Resume from last checkpoint if exists
        JobCheckpoint checkpoint = checkpointService.getCheckpoint(jobId);
        String lastProcessedId = checkpoint != null ? checkpoint.getLastProcessedId() : null;

        try (Stream<DataRecord> records = getRecordsAfter(lastProcessedId)) {
            records.forEach(record -> {
                if (context.isCancelled()) {
                    throw new JobCancelledException();
                }

                processRecord(record);

                // Save checkpoint every 1000 records
                if (record.getIndex() % 1000 == 0) {
                    checkpointService.saveCheckpoint(jobId, record.getId());
                }
            });
        }

        // Clear checkpoint on successful completion
        checkpointService.clearCheckpoint(jobId);
    }
}
```

**Job configuration:**

```java
// Good: Configurable job parameters
@JobConfiguration
public class ProductSyncJobConfig {

    @JobParameter(name = "batchSize", defaultValue = "100")
    private int batchSize;

    @JobParameter(name = "syncMode", defaultValue = "INCREMENTAL")
    private SyncMode syncMode;

    @JobParameter(name = "skipErrors", defaultValue = "true")
    private boolean skipErrors;

    @JobSchedule(cron = "0 0 2 * * ?")  // Daily at 2 AM
    public Class<? extends Job> getJobClass() {
        return ProductSyncJob.class;
    }
}
```

**Job monitoring endpoint:**

```java
// Good: REST endpoint for job status
@Path("/jobs")
public class JobResource {

    @GET
    @Path("/{jobId}/status")
    public Response getJobStatus(@PathParam("jobId") String jobId) {
        JobProgress progress = progressService.getProgress(jobId);

        if (progress == null) {
            throw new NotFoundException("Job not found: " + jobId);
        }

        return Response.ok(JobStatusRO.builder()
            .jobId(jobId)
            .status(progress.getStatus())
            .percentComplete(progress.getPercentComplete())
            .processedCount(progress.getProcessedCount())
            .errorCount(progress.getErrorCount())
            .startTime(progress.getStartTime())
            .estimatedCompletion(progress.getEstimatedCompletion())
            .build()).build();
    }

    @POST
    @Path("/{jobId}/cancel")
    public Response cancelJob(@PathParam("jobId") String jobId) {
        jobService.requestCancellation(jobId);
        return Response.accepted().build();
    }
}
```

**Job best practices:**

| Practice | Description |
|----------|-------------|
| Cancellation support | Check `isCancelled()` regularly |
| Progress tracking | Update progress for visibility |
| Checkpoints | Allow restart from failure point |
| Error isolation | Continue on item failure if possible |
| Batch commits | Don't hold transactions too long |
| Logging | Structured logs for monitoring |

Reference: [ICM Job Framework](https://knowledge.intershop.com/kb/index.php/Display/29230E)
