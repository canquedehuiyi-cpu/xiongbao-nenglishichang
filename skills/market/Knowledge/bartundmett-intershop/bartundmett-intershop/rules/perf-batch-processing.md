---
title: Use Batch Processing for Bulk Operations
impact: HIGH
impactDescription: 10-100× improvement for bulk data operations
tags: performance, batch, bulk, optimization
---

## Use Batch Processing for Bulk Operations

**Impact: HIGH (10-100× improvement for bulk data operations)**

Process large datasets in batches to avoid memory issues and improve throughput. Never load entire datasets into memory.

**Incorrect (loading everything into memory):**

```java
// Bad: Loading all records at once
public void updateAllPrices(BigDecimal multiplier) {
    List<ProductPO> allProducts = productRepository.findAll();  // 100,000+ products!

    for (ProductPO product : allProducts) {
        product.setPrice(product.getPrice().multiply(multiplier));
        productRepository.save(product);  // Individual save
    }
}

// Bad: Creating large collections
public void importProducts(List<ProductData> products) {
    List<ProductPO> toSave = new ArrayList<>();

    for (ProductData data : products) {  // 50,000 items
        ProductPO product = convertToEntity(data);
        toSave.add(product);  // All in memory!
    }

    productRepository.saveAll(toSave);
}
```

**Correct (batch processing):**

```java
// Good: Process in batches with flush and clear
public void updateAllPrices(BigDecimal multiplier) {
    final int BATCH_SIZE = 100;
    int processed = 0;

    ScrollableResults scroll = queryManager.createQuery("FROM ProductPO")
        .scroll(ScrollMode.FORWARD_ONLY);

    try {
        while (scroll.next()) {
            ProductPO product = (ProductPO) scroll.get(0);
            product.setPrice(product.getPrice().multiply(multiplier));

            processed++;

            if (processed % BATCH_SIZE == 0) {
                // Flush changes to DB
                entityManager.flush();
                // Clear persistence context to free memory
                entityManager.clear();

                logger.info("Processed {} products", processed);
            }
        }

        // Final flush
        entityManager.flush();
        logger.info("Completed. Total processed: {}", processed);

    } finally {
        scroll.close();
    }
}

// Good: Batch insert with JDBC batching
@Transactional
public void importProducts(List<ProductData> products) {
    final int BATCH_SIZE = 100;

    for (int i = 0; i < products.size(); i++) {
        ProductPO product = convertToEntity(products.get(i));
        entityManager.persist(product);

        if ((i + 1) % BATCH_SIZE == 0) {
            entityManager.flush();
            entityManager.clear();
        }
    }

    entityManager.flush();
}

// Good: Streaming large result sets
public void exportProducts(OutputStream output) {
    try (Stream<ProductPO> stream = productRepository.streamAll()) {
        stream.forEach(product -> {
            writeToOutput(output, product);
            entityManager.detach(product);  // Free memory
        });
    }
}
```

**Parallel batch processing:**

```java
// Good: Parallel processing with partitioning
public void processLargeDataset(List<String> productIds) {
    final int PARTITION_SIZE = 1000;

    // Split into partitions
    List<List<String>> partitions = Lists.partition(productIds, PARTITION_SIZE);

    // Process partitions in parallel
    partitions.parallelStream().forEach(partition -> {
        // Each partition in its own transaction
        transactionTemplate.execute(status -> {
            for (String productId : partition) {
                processProduct(productId);
            }
            return null;
        });
    });
}

// Good: Async batch processing with progress tracking
public class BatchProcessor {

    @Inject
    private AsyncExecutor asyncExecutor;

    public BatchJob startBatchJob(List<String> itemIds, Consumer<String> processor) {
        BatchJob job = new BatchJob(itemIds.size());
        batchJobRepository.save(job);

        // Process in background
        asyncExecutor.submit(() -> {
            final int BATCH_SIZE = 100;

            for (int i = 0; i < itemIds.size(); i += BATCH_SIZE) {
                int end = Math.min(i + BATCH_SIZE, itemIds.size());
                List<String> batch = itemIds.subList(i, end);

                transactionTemplate.execute(status -> {
                    for (String itemId : batch) {
                        try {
                            processor.accept(itemId);
                            job.incrementSuccess();
                        } catch (Exception e) {
                            job.incrementFailed();
                            job.addError(itemId, e.getMessage());
                        }
                    }
                    return null;
                });

                job.setProgress((i + BATCH_SIZE) * 100 / itemIds.size());
                batchJobRepository.update(job);
            }

            job.setStatus(JobStatus.COMPLETED);
            batchJobRepository.update(job);
        });

        return job;
    }
}
```

**Batch delete optimization:**

```java
// Bad: Individual deletes
public void deleteOldOrders(LocalDate before) {
    List<OrderPO> oldOrders = orderRepository.findByDateBefore(before);
    for (OrderPO order : oldOrders) {
        orderRepository.delete(order);  // N delete queries!
    }
}

// Good: Bulk delete with single query
public void deleteOldOrders(LocalDate before) {
    int deleted = queryManager.createQuery(
        "DELETE FROM OrderPO o WHERE o.createdDate < :before")
        .setParameter("before", before)
        .executeUpdate();

    logger.info("Deleted {} old orders", deleted);
}

// Good: Batched delete with cascade handling
public void deleteOldOrdersWithCascade(LocalDate before) {
    final int BATCH_SIZE = 100;

    List<String> orderIds;
    do {
        orderIds = queryManager.createQuery(
            "SELECT o.id FROM OrderPO o WHERE o.createdDate < :before")
            .setParameter("before", before)
            .setMaxResults(BATCH_SIZE)
            .list();

        if (!orderIds.isEmpty()) {
            // Delete line items first (cascaded)
            queryManager.createQuery(
                "DELETE FROM OrderLineItemPO li WHERE li.order.id IN :ids")
                .setParameterList("ids", orderIds)
                .executeUpdate();

            // Delete orders
            queryManager.createQuery(
                "DELETE FROM OrderPO o WHERE o.id IN :ids")
                .setParameterList("ids", orderIds)
                .executeUpdate();
        }
    } while (!orderIds.isEmpty());
}
```

**Batch processing best practices:**

| Practice | Benefit |
|----------|---------|
| Batch size 50-200 | Balance memory vs DB round trips |
| Flush + clear | Free memory during processing |
| Progress tracking | User visibility for long jobs |
| Error handling | Continue on item failure |
| Transactions per batch | Avoid huge rollbacks |

Reference: [Hibernate Batch Processing](https://docs.jboss.org/hibernate/orm/current/userguide/html_single/Hibernate_User_Guide.html#batch)
