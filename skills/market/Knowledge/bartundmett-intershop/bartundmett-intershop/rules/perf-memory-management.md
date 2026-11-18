---
title: Manage Memory Efficiently
impact: HIGH
impactDescription: prevents OutOfMemory errors and GC pauses
tags: performance, memory, gc, heap
---

## Manage Memory Efficiently

**Impact: HIGH (prevents OutOfMemory errors and GC pauses)**

Efficient memory management prevents heap exhaustion, reduces garbage collection pauses, and maintains consistent response times.

**Incorrect (memory-wasteful patterns):**

```java
// Bad: Loading entire result set into memory
public List<ProductBO> getAllProducts() {
    Query query = em.createQuery("SELECT p FROM ProductPO p");
    return query.getResultList();  // Could be millions of rows!
}

// Bad: String concatenation in loops
public String buildProductList(List<ProductBO> products) {
    String result = "";
    for (ProductBO product : products) {
        result += product.getName() + ", ";  // Creates new String each iteration
    }
    return result;
}

// Bad: Holding references longer than needed
public class ProductCache {
    private Map<String, ProductBO> cache = new HashMap<>();  // Unbounded!

    public void cacheProduct(ProductBO product) {
        cache.put(product.getSKU(), product);  // Never evicts
    }
}

// Bad: Large byte arrays for file processing
public void processImage(File imageFile) throws IOException {
    byte[] data = Files.readAllBytes(imageFile.toPath());  // 50MB in heap!
    processBytes(data);
}
```

**Correct (memory-efficient patterns):**

```java
// Good: Stream large result sets
@Injectable
public class ProductExportService {

    @Inject
    private EntityManager em;

    public void exportAllProducts(OutputStream output) {
        try (Stream<ProductPO> stream = em.createQuery(
                "SELECT p FROM ProductPO p", ProductPO.class)
                .setHint(QueryHints.HINT_FETCH_SIZE, 100)
                .getResultStream()) {

            stream.forEach(product -> {
                writeToOutput(product, output);
                em.detach(product);  // Release from persistence context
            });
        }
    }
}

// Good: StringBuilder for string operations
public String buildProductList(List<ProductBO> products) {
    StringBuilder sb = new StringBuilder(products.size() * 50);  // Pre-size

    for (int i = 0; i < products.size(); i++) {
        if (i > 0) sb.append(", ");
        sb.append(products.get(i).getName());
    }

    return sb.toString();
}

// Good: Bounded cache with eviction
@Injectable
public class ProductCache {

    private static final int MAX_CACHE_SIZE = 10000;

    private final Map<String, ProductBO> cache = new LinkedHashMap<>(
            MAX_CACHE_SIZE, 0.75f, true) {
        @Override
        protected boolean removeEldestEntry(Map.Entry<String, ProductBO> eldest) {
            return size() > MAX_CACHE_SIZE;
        }
    };

    // Or use Guava/Caffeine cache
    private final Cache<String, ProductBO> guavaCache = CacheBuilder.newBuilder()
            .maximumSize(MAX_CACHE_SIZE)
            .expireAfterAccess(Duration.ofMinutes(30))
            .recordStats()
            .build();
}

// Good: Stream file processing
@Injectable
public class ImageProcessingService {

    private static final int BUFFER_SIZE = 8192;

    public void processImage(File imageFile, OutputStream output) throws IOException {
        try (InputStream input = new BufferedInputStream(
                new FileInputStream(imageFile), BUFFER_SIZE)) {

            byte[] buffer = new byte[BUFFER_SIZE];
            int bytesRead;

            while ((bytesRead = input.read(buffer)) != -1) {
                processChunk(buffer, bytesRead, output);
            }
        }
    }
}

// Good: Weak references for non-critical caches
public class TemplateCache {

    private final Map<String, WeakReference<CompiledTemplate>> cache =
            new ConcurrentHashMap<>();

    public CompiledTemplate get(String templateName) {
        WeakReference<CompiledTemplate> ref = cache.get(templateName);
        if (ref != null) {
            CompiledTemplate template = ref.get();
            if (template != null) {
                return template;
            }
        }

        CompiledTemplate template = compileTemplate(templateName);
        cache.put(templateName, new WeakReference<>(template));
        return template;
    }
}

// Good: Object pooling for expensive objects
@Injectable
public class PDFGeneratorPool {

    private final GenericObjectPool<PDFGenerator> pool;

    public PDFGeneratorPool() {
        GenericObjectPoolConfig<PDFGenerator> config = new GenericObjectPoolConfig<>();
        config.setMaxTotal(10);
        config.setMaxIdle(5);
        config.setMinIdle(2);

        pool = new GenericObjectPool<>(new PDFGeneratorFactory(), config);
    }

    public byte[] generatePDF(ReportData data) throws Exception {
        PDFGenerator generator = pool.borrowObject();
        try {
            return generator.generate(data);
        } finally {
            pool.returnObject(generator);
        }
    }
}

// Good: Clear persistence context in batch operations
@Injectable
public class BatchImportService {

    @Inject
    private EntityManager em;

    public void importProducts(List<ProductData> products) {
        int count = 0;

        for (ProductData data : products) {
            ProductPO entity = mapToEntity(data);
            em.persist(entity);

            if (++count % 100 == 0) {
                em.flush();
                em.clear();  // Detach all entities, free memory
            }
        }

        em.flush();
        em.clear();
    }
}
```

**Memory configuration recommendations:**

| Setting | Development | Production |
|---------|-------------|------------|
| Heap Size (-Xmx) | 2G | 8-16G |
| New Gen Ratio | 1/3 | 1/3 |
| GC Algorithm | G1GC | G1GC or ZGC |
| Metaspace | 256M | 512M |

Reference: [Java Performance Tuning](https://knowledge.intershop.com/kb/index.php/Display/2X2867)
