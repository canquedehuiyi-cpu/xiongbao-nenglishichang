---
title: Implement Data Exports Efficiently
impact: MEDIUM
impactDescription: enables reliable large-scale data exports
tags: impex, export, data, bulk, integration
---

## Implement Data Exports Efficiently

**Impact: MEDIUM (enables reliable large-scale data exports)**

Data exports for products, orders, and inventory must be efficient, streaming, and support incremental/delta exports.

**Incorrect (naive export implementation):**

```java
// Bad: Loading all data into memory
public void exportProducts(OutputStream output) throws IOException {
    List<ProductBO> allProducts = productRepository.findAll();  // Millions in memory!

    for (ProductBO product : allProducts) {
        writeLine(output, product);
    }
}

// Bad: No delta export capability
public void exportOrders(OutputStream output) {
    List<OrderBO> orders = orderRepository.findAll();  // Full export every time!
    writeOrders(output, orders);
}

// Bad: Blocking while generating large file
public byte[] generateExportFile() {
    ByteArrayOutputStream baos = new ByteArrayOutputStream();
    // Generate entire file in memory...
    return baos.toByteArray();  // Could be gigabytes!
}
```

**Correct (robust export implementation):**

```java
// Good: Streaming export with cursor
@Injectable
public class ProductExportService {

    @Inject
    private EntityManager em;

    private static final int FETCH_SIZE = 100;

    public void exportProducts(OutputStream output, ExportOptions options)
            throws IOException {

        try (CSVPrinter printer = new CSVPrinter(
                new BufferedWriter(new OutputStreamWriter(output)),
                CSVFormat.DEFAULT.withHeader(getHeaders()))) {

            Query query = em.createQuery(
                "SELECT p FROM ProductPO p ORDER BY p.sku");
            query.setHint(QueryHints.HINT_FETCH_SIZE, FETCH_SIZE);

            try (Stream<ProductPO> stream = query.getResultStream()) {
                stream.forEach(product -> {
                    try {
                        writeProduct(printer, product);
                        em.detach(product);  // Release memory
                    } catch (IOException e) {
                        throw new UncheckedIOException(e);
                    }
                });
            }
        }
    }

    private void writeProduct(CSVPrinter printer, ProductPO product)
            throws IOException {
        printer.printRecord(
            product.getSku(),
            product.getName(),
            product.getPrice(),
            product.getCategory().getName(),
            product.isAvailable()
        );
    }
}

// Good: Delta/incremental export
@Injectable
public class DeltaExportService {

    @Inject
    private ExportCheckpointRepository checkpointRepository;

    public void exportChangedProducts(OutputStream output, String exportId)
            throws IOException {

        // Get last export timestamp
        ExportCheckpoint checkpoint = checkpointRepository.findById(exportId);
        Instant lastExport = checkpoint != null
            ? checkpoint.getLastExportTime()
            : Instant.EPOCH;

        Instant currentTime = Instant.now();

        // Export only changed records
        try (Stream<ProductPO> stream = em.createQuery(
                "SELECT p FROM ProductPO p " +
                "WHERE p.lastModified > :lastExport " +
                "ORDER BY p.lastModified", ProductPO.class)
                .setParameter("lastExport", lastExport)
                .getResultStream()) {

            AtomicInteger count = new AtomicInteger();
            stream.forEach(product -> {
                writeProduct(output, product);
                count.incrementAndGet();
            });

            // Update checkpoint
            saveCheckpoint(exportId, currentTime, count.get());
        }
    }

    // Export deleted records
    public void exportDeletedProducts(OutputStream output, Instant since)
            throws IOException {

        List<AuditLogEntry> deletions = auditLogRepository
            .findByEntityTypeAndActionAndTimestampAfter(
                "Product", "DELETE", since);

        try (CSVPrinter printer = createPrinter(output)) {
            for (AuditLogEntry deletion : deletions) {
                printer.printRecord(
                    deletion.getEntityId(),
                    "DELETED",
                    deletion.getTimestamp()
                );
            }
        }
    }
}

// Good: Async export with progress tracking
@Injectable
public class AsyncExportService {

    @Inject
    private ExportJobRepository jobRepository;

    @Inject
    private StorageService storageService;

    public String startExport(ExportRequest request) {
        ExportJob job = new ExportJob();
        job.setId(UUID.randomUUID().toString());
        job.setType(request.getType());
        job.setStatus(ExportStatus.PENDING);
        job.setCreatedAt(Instant.now());
        job.setCreatedBy(request.getUserId());

        jobRepository.save(job);

        // Execute asynchronously
        asyncExecutor.submit(() -> executeExport(job, request));

        return job.getId();
    }

    @Async
    private void executeExport(ExportJob job, ExportRequest request) {
        try {
            job.setStatus(ExportStatus.RUNNING);
            job.setStartedAt(Instant.now());
            jobRepository.save(job);

            // Generate to temp file
            Path tempFile = Files.createTempFile("export-", ".csv");
            try (OutputStream output = new BufferedOutputStream(
                    Files.newOutputStream(tempFile))) {

                exportProducts(output, job.getId());
            }

            // Upload to storage
            String fileUrl = storageService.upload(tempFile, generateFileName(job));

            job.setStatus(ExportStatus.COMPLETED);
            job.setFileUrl(fileUrl);
            job.setFileSize(Files.size(tempFile));
            job.setCompletedAt(Instant.now());

            // Cleanup temp file
            Files.delete(tempFile);

        } catch (Exception e) {
            job.setStatus(ExportStatus.FAILED);
            job.setErrorMessage(e.getMessage());
            logger.error("Export failed", e);
        }

        jobRepository.save(job);
    }

    public ExportJob getExportStatus(String jobId) {
        return jobRepository.findById(jobId);
    }
}

// Good: Configurable export format
@Injectable
public class ConfigurableExporter {

    public void export(ExportRequest request, OutputStream output)
            throws IOException {

        ExportFormat format = request.getFormat();

        try (ExportWriter writer = createWriter(format, output)) {
            // Write header
            writer.writeHeader(request.getFields());

            // Stream records
            int processed = 0;
            try (Stream<ProductPO> stream = getProductStream(request)) {
                Iterator<ProductPO> iterator = stream.iterator();

                while (iterator.hasNext()) {
                    ProductPO product = iterator.next();
                    writer.writeRecord(mapToFields(product, request.getFields()));
                    processed++;

                    if (processed % 1000 == 0) {
                        writer.flush();
                        updateProgress(request.getJobId(), processed);
                    }
                }
            }

            writer.writeFooter(processed);
        }
    }

    private ExportWriter createWriter(ExportFormat format, OutputStream output) {
        switch (format) {
            case CSV:
                return new CsvExportWriter(output);
            case JSON:
                return new JsonExportWriter(output);
            case XML:
                return new XmlExportWriter(output);
            case XLSX:
                return new ExcelExportWriter(output);
            default:
                throw new IllegalArgumentException("Unsupported format: " + format);
        }
    }
}

// Good: Export with compression
@Injectable
public class CompressedExportService {

    public void exportWithCompression(ExportRequest request, OutputStream output)
            throws IOException {

        try (GZIPOutputStream gzipOut = new GZIPOutputStream(output);
             BufferedWriter writer = new BufferedWriter(
                 new OutputStreamWriter(gzipOut, StandardCharsets.UTF_8))) {

            exportToWriter(request, writer);
        }
    }
}
```

**Export best practices:**

| Practice | Description |
|----------|-------------|
| Stream data | Never load all data into memory |
| Delta exports | Track changes since last export |
| Async processing | Background jobs for large exports |
| Compression | GZIP for large files |
| Chunked writes | Flush periodically |
| Progress tracking | Update status during export |

Reference: [ICM Export Framework](https://knowledge.intershop.com/kb/index.php/Display/29230E)
