---
title: Configure Database Connection Pooling
impact: HIGH
impactDescription: prevents connection exhaustion and improves throughput
tags: performance, database, connection-pool, hikari
---

## Configure Database Connection Pooling

**Impact: HIGH (prevents connection exhaustion and improves throughput)**

Proper connection pool configuration is critical for handling concurrent requests. Misconfigured pools lead to connection timeouts, exhaustion, or wasted resources.

**Incorrect (default or unbounded pool):**

```java
// Bad: No pool configuration - relies on defaults
@Injectable
public class ProductService {

    @Inject
    private DataSource dataSource;

    public List<ProductBO> getProducts() {
        // Each call may create new connection
        try (Connection conn = dataSource.getConnection()) {
            // Query execution
        }
    }
}

// Bad: Pool too large - wastes resources
// application.properties
// connection.pool.size=500  // Far more than needed
// connection.pool.timeout=60000  // Too long timeout

// Bad: Pool too small for traffic
// connection.pool.size=5  // Bottleneck under load
```

**Correct (properly sized and configured pool):**

```java
// Good: HikariCP configuration for ICM
// In appserver configuration or properties

// Sizing formula: connections = (core_count * 2) + effective_spindle_count
// For SSD with 8 cores: (8 * 2) + 1 = 17 connections
hikari.pool.maximumPoolSize=20
hikari.pool.minimumIdle=5
hikari.pool.idleTimeout=300000
hikari.pool.connectionTimeout=30000
hikari.pool.maxLifetime=1800000
hikari.pool.leakDetectionThreshold=60000

// Good: Connection validation
hikari.pool.connectionTestQuery=SELECT 1

// Good: Monitor pool health
@Injectable
public class ConnectionPoolMonitor {

    @Inject
    private HikariDataSource dataSource;

    @Inject
    private MetricsService metricsService;

    @Scheduled(fixedRate = 60000)
    public void recordPoolMetrics() {
        HikariPoolMXBean poolBean = dataSource.getHikariPoolMXBean();

        metricsService.gauge("db.pool.active", poolBean.getActiveConnections());
        metricsService.gauge("db.pool.idle", poolBean.getIdleConnections());
        metricsService.gauge("db.pool.waiting", poolBean.getThreadsAwaitingConnection());
        metricsService.gauge("db.pool.total", poolBean.getTotalConnections());

        // Alert if pool is near exhaustion
        double utilization = (double) poolBean.getActiveConnections() /
                            dataSource.getMaximumPoolSize();
        if (utilization > 0.8) {
            logger.warn("Connection pool utilization high: {}%", utilization * 100);
        }
    }
}

// Good: Proper connection handling with try-with-resources
@Injectable
public class ProductRepository {

    @Inject
    private DataSource dataSource;

    public List<ProductPO> findBySKUs(List<String> skus) {
        String sql = buildInClause("SELECT * FROM products WHERE sku IN (?)", skus.size());

        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {

            for (int i = 0; i < skus.size(); i++) {
                stmt.setString(i + 1, skus.get(i));
            }

            try (ResultSet rs = stmt.executeQuery()) {
                return mapResults(rs);
            }

        } catch (SQLException e) {
            throw new RepositoryException("Failed to query products", e);
        }
        // Connection automatically returned to pool
    }
}

// Good: Connection pool per application context
public class DataSourceConfiguration {

    public HikariDataSource createDataSource(ApplicationContext context) {
        HikariConfig config = new HikariConfig();

        // Size based on application type
        if (context.isBackoffice()) {
            config.setMaximumPoolSize(10);  // Lower for admin traffic
        } else if (context.isStorefront()) {
            config.setMaximumPoolSize(30);  // Higher for customer traffic
        }

        config.setPoolName(context.getName() + "-pool");
        config.setRegisterMbeans(true);  // Enable JMX monitoring

        return new HikariDataSource(config);
    }
}
```

**Connection pool sizing guidelines:**

| Application Type | Max Pool Size | Min Idle | Timeout |
|------------------|---------------|----------|---------|
| Storefront | 20-30 | 5-10 | 30s |
| Back Office | 10-15 | 3-5 | 60s |
| Batch Jobs | 5-10 | 2 | 120s |
| REST API | 15-25 | 5 | 30s |

Reference: [HikariCP Configuration](https://github.com/brettwooldridge/HikariCP)
