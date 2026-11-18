# Intershop ICM Best Practices

A structured repository for creating and maintaining Intershop Commerce Management (ICM) Best Practices optimized for agents and LLMs.

## Structure

- `rules/` - Individual rule files (one per rule)
  - `_sections.md` - Section metadata (titles, impacts, descriptions)
  - `_template.md` - Template for creating new rules
  - `area-description.md` - Individual rule files
- `metadata.json` - Document metadata (version, organization, abstract)
- __`AGENTS.md`__ - Compiled output (generated)
- __`SKILL.md`__ - Quick reference for the skill

## Getting Started

1. Browse rules by category:
   - `custom-*` - Customization patterns
   - `perf-*` - Performance optimization
   - `state-*` - State management
   - `b2b-*` - B2B features
   - `rest-*` - REST API development
   - `cartridge-*` - Cartridge architecture
   - `db-*` - Database operations
   - `pipeline-*` - Pipeline development
   - `guice-*` - Dependency injection
   - `devops-*` - Deployment & DevOps

2. Read the full compiled guide: `AGENTS.md`

## Creating a New Rule

1. Copy `rules/_template.md` to `rules/area-description.md`
2. Choose the appropriate area prefix:
   - `custom-` for Customization Patterns (Section 1)
   - `perf-` for Performance Optimization (Section 2)
   - `state-` for State Management (Section 3)
   - `b2b-` for B2B Features (Section 4)
   - `rest-` for REST API Development (Section 5)
   - `cartridge-` for Cartridge Architecture (Section 6)
   - `db-` for Database & Persistence (Section 7)
   - `pipeline-` for Pipeline Development (Section 8)
   - `guice-` for Dependency Injection (Section 9)
   - `devops-` for Deployment & DevOps (Section 10)
3. Fill in the frontmatter and content
4. Ensure you have clear examples with explanations

## Rule File Structure

Each rule file should follow this structure:

```markdown
---
title: Rule Title Here
impact: MEDIUM
impactDescription: Optional description
tags: tag1, tag2, tag3
---

## Rule Title Here

Brief explanation of the rule and why it matters.

**Incorrect (description of what's wrong):**

```java
// Bad code example
```

**Correct (description of what's right):**

```java
// Good code example
```

Reference: [Link](https://knowledge.intershop.com)
```

## Impact Levels

- `CRITICAL` - Highest priority, major impact on maintainability/performance
- `HIGH` - Significant improvements in code quality or performance
- `MEDIUM-HIGH` - Moderate-high gains
- `MEDIUM` - Moderate improvements
- `LOW-MEDIUM` - Low-medium gains
- `LOW` - Incremental improvements

## Key References

- [Intershop Knowledge Base](https://knowledge.intershop.com)
- [Intershop Support](https://support.intershop.com)
- [Intershop PWA GitHub](https://github.com/intershop/intershop-pwa)
- [Intershop Commerce Platform](https://www.intershop.com/en/e-commerce-platform)

## Contributing

When adding or modifying rules:

1. Use the correct filename prefix for your section
2. Follow the `_template.md` structure
3. Include clear bad/good examples with explanations
4. Add appropriate tags
5. Reference official Intershop documentation

## Acknowledgments

Based on official Intershop documentation and best practices from the Intershop Engineering team.
