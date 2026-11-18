# Sections

This file defines all sections, their ordering, impact levels, and descriptions.
The section ID (in parentheses) is the filename prefix used to group rules.

---

## 1. Customization Patterns (custom)

**Impact:** CRITICAL
**Description:** Proper customization patterns ensure upgrade-safe modifications, minimize merge conflicts, and maintain long-term maintainability. Poor customization is the #1 source of migration pain.

## 2. Performance Optimization (perf)

**Impact:** CRITICAL
**Description:** Optimizing database queries, caching strategies, memory management, and connection pooling directly impacts user experience and system scalability.

## 3. State Management & Data Flow (state)

**Impact:** CRITICAL
**Description:** Proper business object handling, repository patterns, and data flow architecture are essential for maintainable and performant ICM applications.

## 4. B2B Features (b2b)

**Impact:** CRITICAL
**Description:** B2B-specific features like punchout, customer-specific pricing, organization hierarchy, approval workflows, budget management, quote management, and role-based access control require careful implementation to meet enterprise requirements.

## 5. REST API Development (rest)

**Impact:** HIGH
**Description:** Properly designed REST resources with correct handlers, resource objects, authentication, pagination, error handling, versioning, and HATEOAS ensure secure and maintainable API endpoints.

## 6. Cartridge Architecture (cartridge)

**Impact:** HIGH
**Description:** Correct cartridge organization, dependency management, and layering patterns form the foundation of maintainable ICM customizations.

## 7. Database & Persistence (db)

**Impact:** MEDIUM-HIGH
**Description:** Proper use of persistent objects, ORM patterns, transaction management, optimistic locking, PO lifecycle, and database initialization ensures data integrity and performance.

## 8. Pipeline & Pipelet Development (pipeline)

**Impact:** MEDIUM
**Description:** Following pipeline best practices, proper transaction handling, and error handling ensures maintainable business logic implementation.

## 9. Dependency Injection & Guice (guice)

**Impact:** MEDIUM
**Description:** Proper use of Guice for dependency injection enables testability and extensibility of ICM components.

## 10. Deployment & DevOps (devops)

**Impact:** LOW-MEDIUM
**Description:** Container-based deployment, Kubernetes configuration, and CI/CD integration patterns for reliable releases.

## 11. Testing (test)

**Impact:** HIGH
**Description:** Comprehensive testing strategies including unit tests, integration tests, REST API testing, mock repositories, and test data builders ensure code quality and reliability.

## 12. Security (security)

**Impact:** CRITICAL
**Description:** Input validation, SQL injection prevention, XSS prevention, CSRF protection, sensitive data handling, and access control patterns are essential for secure applications.

## 13. Logging & Observability (logging)

**Impact:** MEDIUM
**Description:** Structured logging, correlation IDs, appropriate log levels, and avoiding sensitive data in logs enable effective debugging and monitoring.

## 14. ISML Templates (template)

**Impact:** MEDIUM
**Description:** ISML template best practices, include patterns, loop optimization, and fragment caching improve frontend performance and maintainability.

## 15. Job & Batch Processing (job)

**Impact:** MEDIUM
**Description:** Proper job implementation with progress tracking, error handling, checkpointing, and cancellation support enables reliable batch operations.

## 16. Events & Messaging (event)

**Impact:** MEDIUM
**Description:** Domain event publishing, reliable event consumption, idempotency, and event patterns enable loose coupling and scalable architectures.

## 17. ImpEx Data Exchange (impex)

**Impact:** MEDIUM
**Description:** Efficient data import and export patterns with streaming, validation, resumability, and delta processing enable reliable data integration.

## 18. Search (search)

**Impact:** HIGH
**Description:** Solr search customization, query building, and faceting patterns ensure relevant search results and optimal performance.

## 19. Internationalization (i18n)

**Impact:** HIGH
**Description:** Proper multi-language support, locale-aware formatting for dates/numbers/currencies, and resource bundle management enable global market reach.

## 20. Monitoring & Observability (monitoring)

**Impact:** HIGH
**Description:** APM integration, metrics collection, distributed tracing, health checks, and alerting enable proactive performance management and issue detection.
