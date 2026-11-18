---
id: SKL-elk-ELKSTACK
name: Elk Stack
description: 'The ELK Stack (Elasticsearch, Logstash, Kibana) is a powerful set of
  tools for searching, analyzing, and visualizing data in real-time. This skill covers
  ELK stack setup, configuration, log shipping, '
version: 1.0.0
status: active
owner: '@cerebra-team'
last_updated: '2026-02-22'
category: Backend
tags:
- api
- backend
- server
- database
stack:
- Python
- Node.js
- REST API
- GraphQL
difficulty: Intermediate
---

# Elk Stack

## Skill Profile
*(Select at least one profile to enable specific modules)*
- [ ] **DevOps**
- [x] **Backend**
- [ ] **Frontend**
- [ ] **AI-RAG**
- [ ] **Security Critical**

## Overview
The ELK Stack (Elasticsearch, Logstash, Kibana) is a powerful set of tools for searching, analyzing, and visualizing data in real-time. This skill covers ELK stack setup, configuration, log shipping, index management, queries, visualizations, dashboards, alerts, and production deployment with security and high availability.

## Why This Matters
- **Centralized Observability**: Provides unified platform for log aggregation, search, and analysis across all services
- **Real-time Insights**: Enables immediate visibility into system health, errors, and performance metrics
- **Scalable Architecture**: Distributed design handles massive log volumes with horizontal scaling capabilities
- **Rich Visualizations**: Custom dashboards and visualizations make complex data actionable for operations teams

---

## Core Concepts & Rules

### 1. Core Principles
- Follow established patterns and conventions
- Maintain consistency across codebase
- Document decisions and trade-offs

### 2. Implementation Guidelines
- Start with the simplest viable solution
- Iterate based on feedback and requirements
- Test thoroughly before deployment


## Inputs / Outputs / Contracts
* **Inputs**:
  - Application logs in JSON or text format
  - Log file paths from services (e.g., /var/log/application/*.log)
  - Environment variables for configuration (ENVIRONMENT, HOSTNAME)
  - Elasticsearch connection details (hosts, ports, credentials)
  - Index template and lifecycle policy configurations

* **Entry Conditions**:
  - Docker and Docker Compose installed
  - Sufficient disk space for log storage (minimum 50GB for production)
  - Network connectivity between ELK components
  - Application services producing structured logs

* **Outputs**:
  - Configured ELK stack with Elasticsearch, Logstash, Kibana running
  - Index templates and lifecycle policies applied
  - Logstash pipelines configured for log processing
  - Kibana index patterns, visualizations, and dashboards
  - Alert rules configured for monitoring

* **Artifacts Required (Deliverables)**:
  - docker-compose.yml file with ELK stack services
  - Logstash pipeline configuration files
  - Elasticsearch index templates and ILM policies
  - Filebeat configuration for log shipping
  - Kibana saved objects (index patterns, visualizations, dashboards)
  - Application logging configuration examples (Node.js, Python)

* **Acceptance Evidence**:
  - Screenshot of Kibana Discover showing indexed logs
  - Screenshot of functional dashboard with visualizations
  - Log showing successful log ingestion from Filebeat
  - Alert notification test result

* **Success Criteria**:
  - Logs are ingested and searchable within 30 seconds of generation
  - Index lifecycle policy automatically manages index rollover and deletion
  - Kibana dashboards load in under 5 seconds
  - Alert notifications trigger within 1 minute of threshold breach

## Skill Composition
* **Depends on**: [docker-deployment](../../69-platform-engineering-lite/deployment-patterns/SKILL.md), [logging-standards](../../64-meta-standards/logging-metrics-tracing-standard/SKILL.md)
* **Compatible with**: [prometheus-metrics](./prometheus-metrics/SKILL.md), [grafana-dashboards](./grafana-dashboards/SKILL.md), [distributed-tracing](./distributed-tracing/SKILL.md)
* **Conflicts with**: None - ELK stack can coexist with other monitoring tools
* **Related Skills**: [performance-monitoring](./performance-monitoring/SKILL.md), [error-tracking](./error-tracking/SKILL.md)

---

## Quick Start / Implementation Example

1. Review requirements and constraints
2. Set up development environment
3. Implement core functionality following patterns
4. Write tests for critical paths
5. Run tests and fix issues
6. Document any deviations or decisions

```python
# Example implementation following best practices
def example_function():
    # Your implementation here
    pass
```


## Assumptions / Constraints / Non-goals

* **Assumptions**:
  - Development environment is properly configured
  - Required dependencies are available
  - Team has basic understanding of domain
* **Constraints**:
  - Must follow existing codebase conventions
  - Time and resource limitations
  - Compatibility requirements
* **Non-goals**:
  - This skill does not cover edge cases outside scope
  - Not a replacement for formal training


## Compatibility & Prerequisites

* **Supported Versions**:
  - Python 3.8+
  - Node.js 16+
  - Modern browsers (Chrome, Firefox, Safari, Edge)
* **Required AI Tools**:
  - Code editor (VS Code recommended)
  - Testing framework appropriate for language
  - Version control (Git)
* **Dependencies**:
  - Language-specific package manager
  - Build tools
  - Testing libraries
* **Environment Setup**:
  - `.env.example` keys: `API_KEY`, `DATABASE_URL` (no values)


## Test Scenario Matrix (QA Strategy)

| Type | Focus Area | Required Scenarios / Mocks |
| :--- | :--- | :--- |
| **Unit** | Core Logic | Must cover primary logic and at least 3 edge/error cases. Target minimum 80% coverage |
| **Integration** | DB / API | All external API calls or database connections must be mocked during unit tests |
| **E2E** | User Journey | Critical user flows to test |
| **Performance** | Latency / Load | Benchmark requirements |
| **Security** | Vuln / Auth | SAST/DAST or dependency audit |
| **Frontend** | UX / A11y | Accessibility checklist (WCAG), Performance Budget (Lighthouse score) |


## Technical Guardrails & Security Threat Model

### 1. Security & Privacy (Threat Model)
* **Top Threats**: Injection attacks, authentication bypass, data exposure
- [ ] **Data Handling**: Sanitize all user inputs to prevent Injection attacks. Never log raw PII
- [ ] **Secrets Management**: No hardcoded API keys. Use Env Vars/Secrets Manager
- [ ] **Authorization**: Validate user permissions before state changes

### 2. Performance & Resources
- [ ] **Execution Efficiency**: Consider time complexity for algorithms
- [ ] **Memory Management**: Use streams/pagination for large data
- [ ] **Resource Cleanup**: Close DB connections/file handlers in finally blocks

### 3. Architecture & Scalability
- [ ] **Design Pattern**: Follow SOLID principles, use Dependency Injection
- [ ] **Modularity**: Decouple logic from UI/Frameworks

### 4. Observability & Reliability
- [ ] **Logging Standards**: Structured JSON, include trace IDs `request_id`
- [ ] **Metrics**: Track `error_rate`, `latency`, `queue_depth`
- [ ] **Error Handling**: Standardized error codes, no bare except
- [ ] **Observability Artifacts**:
    - **Log Fields**: timestamp, level, message, request_id
    - **Metrics**: request_count, error_count, response_time
    - **Dashboards/Alerts**: High Error Rate > 5%


## Agent Directives & Error Recovery
*(ข้อกำหนดสำหรับ AI Agent ในการคิดและแก้ปัญหาเมื่อเกิดข้อผิดพลาด)*

- **Thinking Process**: Analyze root cause before fixing. Do not brute-force.
- **Fallback Strategy**: Stop after 3 failed test attempts. Output root cause and ask for human intervention/clarification.
- **Self-Review**: Check against Guardrails & Anti-patterns before finalizing.
- **Output Constraints**: Output ONLY the modified code block. Do not explain unless asked.


## Definition of Done (DoD) Checklist

- [ ] Tests passed + coverage met
- [ ] Lint/Typecheck passed
- [ ] Logging/Metrics/Trace implemented
- [ ] Security checks passed
- [ ] Documentation/Changelog updated
- [ ] Accessibility/Performance requirements met (if frontend)


## Anti-patterns / Pitfalls

* ⛔ **Don't**: Log PII, catch-all exception, N+1 queries
* ⚠️ **Watch out for**: Common symptoms and quick fixes
* 💡 **Instead**: Use proper error handling, pagination, and logging


## Reference Links & Examples

* Internal documentation and examples
* Official documentation and best practices
* Community resources and discussions


## Versioning & Changelog

* **Version**: 1.0.0
* **Changelog**:
  - 2026-02-22: Initial version with complete template structure

