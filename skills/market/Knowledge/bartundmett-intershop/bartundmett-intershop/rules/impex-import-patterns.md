---
title: Implement Data Imports Efficiently
impact: MEDIUM
impactDescription: enables reliable large-scale data updates
tags: impex, import, data, bulk, migration
---

## Implement Data Imports Efficiently

**Impact: MEDIUM (enables reliable large-scale data updates)**

Data imports for products, prices, and inventory must be efficient, resumable, and provide clear progress/error feedback.

**Incorrect (naive import implementation):**

```java
// Bad: Loading entire file into memory
public void importProducts(File csvFile) {
    List<String[]> allRows = CSVReader.readAll(csvFile);  // 1M rows in memory!

    for (String[] row : allRows) {
        Product product = parseProduct(row);
        productRepository.save(product);  // Individual save
    }
}

// Bad: No validation, no error handling
public void importPrices(InputStream input) {
    BufferedReader reader = new BufferedReader(new InputStreamReader(input));
    String line;
    while ((line = reader.readLine()) != null) {
        String[] parts = line.split(",");
        String sku = parts[0];
        BigDecimal price = new BigDecimal(parts[1]);  // NumberFormatException?

        Product product = productRepository.findBySku(sku);  // null?
        product.setPrice(price);
        productRepository.save(product);
    }
}
```

**Correct (robust import implementation):**

```java
// Good: Streaming import with batching
@Injectable
public class ProductImportService {

    private static final int BATCH_SIZE = 100;

    @Inject
    private ProductRepository productRepository;

    @Inject
    private ImportProgressService progressService;

    public ImportResult importProducts(InputStream input, String importId) {
        ImportResult result = new ImportResult();

        try (CSVParser parser = CSVFormat.DEFAULT
                .withFirstRecordAsHeader()
                .parse(new InputStreamReader(input))) {

            List<ProductPO> batch = new ArrayList<>();
            int lineNumber = 0;

            for (CSVRecord record : parser) {
                lineNumber++;

                try {
                    // Validate record
                    ValidationResult validation = validateRecord(record, lineNumber);
                    if (!validation.isValid()) {
                        result.addError(lineNumber, validation.getErrors());
                        continue;
                    }

                    // Parse and add to batch
                    ProductPO product = parseProduct(record);
                    batch.add(product);

                    if (batch.size() >= BATCH_SIZE) {
                        saveBatch(batch);
                        result.addProcessed(batch.size());
                        batch.clear();

                        progressService.updateProgress(importId, lineNumber);
                    }

                } catch (Exception e) {
                    result.addError(lineNumber, "Unexpected error: " + e.getMessage());
                    logger.warn("Import error at line {}", lineNumber, e);
                }
            }

            // Save remaining batch
            if (!batch.isEmpty()) {
                saveBatch(batch);
                result.addProcessed(batch.size());
            }

            result.setSuccess(true);

        } catch (IOException e) {
            result.setSuccess(false);
            result.setError("Failed to read import file: " + e.getMessage());
        }

        return result;
    }

    private ValidationResult validateRecord(CSVRecord record, int lineNumber) {
        List<String> errors = new ArrayList<>();

        // Required fields
        if (StringUtils.isBlank(record.get("sku"))) {
            errors.add("SKU is required");
        }
        if (StringUtils.isBlank(record.get("name"))) {
            errors.add("Name is required");
        }

        // Format validation
        String priceStr = record.get("price");
        if (StringUtils.isNotBlank(priceStr)) {
            try {
                new BigDecimal(priceStr);
            } catch (NumberFormatException e) {
                errors.add("Invalid price format: " + priceStr);
            }
        }

        return new ValidationResult(errors.isEmpty(), errors);
    }

    @Transactional
    private void saveBatch(List<ProductPO> products) {
        // Upsert pattern - update if exists, insert if not
        for (ProductPO product : products) {
            ProductPO existing = productRepository.findBySku(product.getSku());
            if (existing != null) {
                updateProduct(existing, product);
            } else {
                productRepository.save(product);
            }
        }
    }
}

// Good: Import with preview/dry-run
public class ImportPreviewService {

    public ImportPreview previewImport(InputStream input, int maxRows) {
        ImportPreview preview = new ImportPreview();

        try (CSVParser parser = CSVFormat.DEFAULT
                .withFirstRecordAsHeader()
                .parse(new InputStreamReader(input))) {

            int count = 0;
            for (CSVRecord record : parser) {
                if (count >= maxRows) break;

                PreviewRow row = new PreviewRow();
                row.setLineNumber(count + 1);
                row.setData(record.toMap());

                // Validate
                ValidationResult validation = validateRecord(record, count + 1);
                row.setValid(validation.isValid());
                row.setErrors(validation.getErrors());

                // Check if update or insert
                String sku = record.get("sku");
                boolean exists = productRepository.existsBySku(sku);
                row.setAction(exists ? "UPDATE" : "INSERT");

                preview.addRow(row);
                count++;
            }

            preview.setTotalRows(count);
        }

        return preview;
    }
}
```

**Import with resumability:**

```java
// Good: Resumable import with checkpoints
public class ResumableImportService {

    public void importWithCheckpoint(String importId, File file) {
        ImportCheckpoint checkpoint = checkpointService.get(importId);
        long skipLines = checkpoint != null ? checkpoint.getLastLine() : 0;

        try (Stream<String> lines = Files.lines(file.toPath()).skip(skipLines)) {
            AtomicLong currentLine = new AtomicLong(skipLines);

            lines.forEach(line -> {
                long lineNum = currentLine.incrementAndGet();

                processLine(line, lineNum);

                if (lineNum % 1000 == 0) {
                    checkpointService.save(importId, lineNum);
                }
            });

            checkpointService.complete(importId);
        }
    }
}
```

**Import result format:**

```json
{
  "success": true,
  "totalRows": 10000,
  "processed": 9950,
  "errors": 50,
  "errorDetails": [
    { "line": 125, "errors": ["Invalid price format: abc"] },
    { "line": 340, "errors": ["SKU not found: XYZ123"] }
  ],
  "duration": "PT2M30S",
  "importId": "import-2026-01-24-001"
}
```

**Import best practices:**

| Practice | Description |
|----------|-------------|
| Stream, don't load | Process line by line |
| Batch saves | Commit every N records |
| Validate first | Check format before processing |
| Preview mode | Dry run before actual import |
| Checkpoints | Enable resume on failure |
| Detailed errors | Report line number and reason |

Reference: [ICM Import Framework](https://knowledge.intershop.com/kb/index.php/Display/29230E)
