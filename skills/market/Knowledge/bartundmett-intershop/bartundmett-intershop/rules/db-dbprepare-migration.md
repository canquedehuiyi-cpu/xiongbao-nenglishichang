---
title: Use DBPrepare for Database Initialization and Migration
impact: MEDIUM-HIGH
impactDescription: ensures reliable database updates and reduced deployment time
tags: database, dbprepare, migration, initialization, deployment
---

## Use DBPrepare for Database Initialization and Migration

**Impact: MEDIUM-HIGH (ensures reliable database updates and reduced deployment time)**

DBPrepare replaces the older DBInit and DBMigrate tools, providing unified database schema and data management with improved performance through incremental updates.

**Incorrect (legacy DBInit/DBMigrate approach):**

```java
// Bad: Old-style DBInit class with manual version management
public class ProductDBInit extends AbstractDbInitClass {

    @Override
    protected void execute() throws Exception {
        // Manual schema creation without tracking
        executeSQL("CREATE TABLE IF NOT EXISTS PRODUCT ...");
        executeSQL("CREATE INDEX IF NOT EXISTS ...");

        // No version tracking
        // No incremental updates
        // Runs every deployment!
    }
}

// Bad: Separate migration without coordination
public class ProductDBMigrate extends AbstractDbMigrateClass {

    @Override
    protected void execute(String fromVersion, String toVersion) {
        // Manual version comparison
        if (compareVersions(fromVersion, "7.10.0") < 0) {
            // May run unnecessarily or be skipped incorrectly
        }
    }
}
```

**Correct (DBPrepare approach):**

```java
// Good: DBPrepare step with proper versioning
public class ProductDBPreparer implements DBPreparer {

    @Override
    public List<DBPreparerStep> getSteps() {
        return Arrays.asList(
            // Each step has unique key - runs only once
            new DBPreparerStep("PRODUCT_001", this::createProductTable),
            new DBPreparerStep("PRODUCT_002", this::addDescriptionColumn),
            new DBPreparerStep("PRODUCT_003", this::createProductIndex),
            new DBPreparerStep("PRODUCT_004", this::migrateProductData)
        );
    }

    private void createProductTable(DBPreparerContext context) {
        context.executeSQL("""
            CREATE TABLE PRODUCT (
                ID VARCHAR(256) NOT NULL,
                SKU VARCHAR(100) NOT NULL,
                NAME VARCHAR(500),
                PRICE DECIMAL(19,4),
                CONSTRAINT PK_PRODUCT PRIMARY KEY (ID)
            )
        """);
    }

    private void addDescriptionColumn(DBPreparerContext context) {
        context.executeSQL("""
            ALTER TABLE PRODUCT ADD COLUMN DESCRIPTION TEXT
        """);
    }

    private void createProductIndex(DBPreparerContext context) {
        context.executeSQL("""
            CREATE INDEX IDX_PRODUCT_SKU ON PRODUCT (SKU)
        """);
    }

    private void migrateProductData(DBPreparerContext context) {
        // Data migration runs once per environment
        context.executeSQL("""
            UPDATE PRODUCT SET DESCRIPTION = 'Default description'
            WHERE DESCRIPTION IS NULL
        """);
    }
}
```

**Register preparer in configuration:**

```properties
# migration.properties
# Package naming: com.intershop.*.<cartridge>.dbinit.preparer.*
com.mycompany.product.dbinit.preparer.ProductDBPreparer=enabled
```

**Step naming conventions:**

```java
// Good: Good step naming - sortable, descriptive
new DBPreparerStep("PRODUCT_001_CREATE_TABLE", this::createTable),
new DBPreparerStep("PRODUCT_002_ADD_INDEXES", this::addIndexes),
new DBPreparerStep("PRODUCT_003_MIGRATE_DATA_V7_10", this::migrateFromV710),
new DBPreparerStep("PRODUCT_004_ADD_CATEGORY_FK", this::addCategoryFK),

// Bad: Bad step naming
new DBPreparerStep("create", ...),  // Too generic, will conflict
new DBPreparerStep("fix-bug", ...),  // Not sortable
```

**Handling conditional migrations:**

```java
public class ConditionalMigrationPreparer implements DBPreparer {

    @Override
    public List<DBPreparerStep> getSteps() {
        return Arrays.asList(
            new DBPreparerStep("MIGRATE_001", this::migrateIfNeeded)
        );
    }

    private void migrateIfNeeded(DBPreparerContext context) {
        // Check if migration is needed
        boolean needsMigration = context.executeQuery(
            "SELECT COUNT(*) FROM PRODUCT WHERE OLD_COLUMN IS NOT NULL"
        ).getInt(1) > 0;

        if (needsMigration) {
            context.executeSQL("""
                UPDATE PRODUCT SET NEW_COLUMN = OLD_COLUMN
                WHERE NEW_COLUMN IS NULL
            """);
        }
        // Step is still marked complete even if no-op
    }
}
```

**DBPrepare advantages:**

| Feature | DBInit/DBMigrate | DBPrepare |
|---------|------------------|-----------|
| Execution tracking | Manual | Automatic per-step |
| Incremental updates | Limited | Full support |
| Deployment time | Full run each time | Only new steps |
| Rollback support | Manual | Framework support |
| Version coordination | Separate tools | Unified |

Reference: [Concept - DBMigrate and DBInit](https://knowledge.intershop.com/kb/index.php/Display/28X093)
