---
name: delegation-router
description: Invoke when deciding which agent handles a task. Provides routing decisions based on task type, scale classification, and agent capabilities, outputting a sequenced routing plan with parallel opportunities.
---

# Delegation Router

A technology-agnostic skill for determining which agent should handle a given task or subtask.

## Core Purpose

Route tasks to the most appropriate agent based on:
- Task type and requirements
- Agent capabilities and specializations
- Task dependencies
- Resource efficiency

## Agent Routing Matrix

### Agents and Their Domains

```yaml
goal-clarifier:
  domain: "Intent clarification and acceptance criteria"
  handles_directly:
    - "Ambiguity resolution"
    - "Acceptance criteria generation"

task-scale-evaluator:
  domain: "Task complexity assessment"
  handles_directly:
    - "Scale classification"
    - "Subtask decomposition"
    - "Parallel group identification"

design-architect:
  domain: "Architecture and design specifications"
  handles_directly:
    - "Architecture design"
    - "Component specification"

code-developer:
  domain: "Production code implementation"
  handles_directly:
    - "Feature implementation"
    - "Bug fixes"
    - "Code changes"

test-developer:
  domain: "Test code implementation"
  handles_directly:
    - "Unit test creation"
    - "Integration test creation"

test-executor:
  domain: "Test execution and result analysis"
  handles_directly:
    - "Test suite execution"
    - "Result categorization"

test-failure-debugger:
  domain: "Test failure analysis"
  handles_directly:
    - "Root cause analysis"
    - "Fix recommendations"

quality-reviewer:
  domain: "Code quality assessment"
  handles_directly:
    - "Code review"
    - "Quality scoring"

deliverable-evaluator:
  domain: "Final deliverable evaluation"
  handles_directly:
    - "Acceptance criteria evaluation"
    - "Pass/fail verdict"

doc-updater:
  domain: "Documentation maintenance"
  handles_directly:
    - "README updates"
    - "Documentation sync"
```

## Routing Decision Logic

### By Task Type

```yaml
task_type_routing:
  code_implementation:
    primary: code-developer
    prerequisites:
      large_tasks: [design-architect]
    followup: [test-executor, quality-reviewer]

  bug_fix:
    primary: code-developer
    prerequisites: []
    followup: [test-executor]

  test_implementation:
    primary: test-developer
    followup: [test-executor]

  test_execution:
    primary: test-executor
    on_failure: test-failure-debugger
    on_success: quality-reviewer

  quality_review:
    primary: quality-reviewer
    on_issues: code-developer
    on_pass: deliverable-evaluator

  requirements:
    primary: goal-clarifier

  architecture:
    primary: design-architect
    when: "New module or significant changes"

  documentation:
    primary: doc-updater
```

### By Task Scale

```yaml
scale_routing:
  trivial:
    agents: [code-developer]
    skip: [design-architect, quality-reviewer, deliverable-evaluator]

  small:
    required: [code-developer, test-executor, deliverable-evaluator]
    optional: [quality-reviewer]
    skip: [design-architect]

  medium:
    required: [code-developer, test-executor, quality-reviewer, deliverable-evaluator]
    optional: [design-architect]

  large:
    required: [design-architect, code-developer, test-executor, quality-reviewer, deliverable-evaluator]
```

### Team Task Dependencies

```yaml
dependency_patterns:
  standard_implementation:
    - implement (no deps)
    - test (blockedBy: implement)
    - review (blockedBy: implement)
    - evaluate (blockedBy: test, review)

  with_architecture:
    - design (no deps)
    - implement (blockedBy: design)
    - test (blockedBy: implement)
    - review (blockedBy: implement)
    - evaluate (blockedBy: test, review)

  with_debugging:
    - implement (no deps)
    - test (blockedBy: implement)
    - debug (blockedBy: test) # only if tests fail
    - fix (blockedBy: debug)
    - retest (blockedBy: fix)
    - review (blockedBy: retest)
    - evaluate (blockedBy: retest, review)
```

## Routing Algorithm

### Step 1: Identify Task Type

```yaml
classify_task:
  implementation:
    indicators: ["implement", "add", "create", "build"]
  bug_fix:
    indicators: ["fix", "resolve", "correct", "debug"]
  review:
    indicators: ["review", "check", "assess"]
  test:
    indicators: ["test", "verify", "validate"]
  requirements:
    indicators: ["clarify", "define", "specify"]
  documentation:
    indicators: ["document", "update docs", "README"]
```

### Step 2: Check Scale Requirements

```yaml
scale_check:
  - Get scale from task-scale-evaluator
  - Apply scale_routing rules
  - Identify required agents
  - Identify optional agents
```

### Step 3: Determine Dependencies

```yaml
dependency_rules:
  dependencies_first:
    - design-architect before code-developer (large)
    - code-developer before test-executor
    - test-executor and quality-reviewer can run in parallel (both after code-developer)

  parallel_when_possible:
    - "Independent subtasks can run in parallel"
    - "test and review run in parallel after implementation"
```

### Step 4: Generate Routing Plan

```yaml
routing_plan:
  tasks:
    - agent: "<agent_name>"
      task: "<specific task>"
      blockedBy: []

  parallel_groups:
    - group: 1
      agents: ["<independent agents>"]
    - group: 2
      agents: ["<agents depending on group 1>"]
```

## Output Format

```yaml
routing_decision:
  task_type: "<classified type>"
  scale: "<task scale>"

  routing_plan:
    - step: 1
      agent: "<agent_name>"
      task: "<what to do>"
      required: true|false
      blockedBy: []

    - step: 2
      agent: "<agent_name>"
      task: "<what to do>"
      required: true|false
      blockedBy: [1]

  skip_agents:
    - agent: "<agent_name>"
      reason: "<why skipped>"

  parallel_opportunities:
    - group: ["<agent1>", "<agent2>"]
      reason: "<why parallel is possible>"
```

## Prohibited Routing

```yaml
never_route:
  implementation:
    to: [test-executor, quality-reviewer, deliverable-evaluator]
    exclusive: code-developer

  quality_judgment:
    to: [code-developer]
    exclusive: [quality-reviewer, deliverable-evaluator]

  test_execution:
    to: [code-developer, quality-reviewer]
    exclusive: test-executor
```

## Integration

### Used By

```yaml
primary_users:
  - "/dev-workflow command": "Task routing decisions during team orchestration"

secondary_users:
  - task-scale-evaluator: "Routing recommendations in scale output"
```

### Project-Specific Routing

Project-specific routing overrides can be defined in the project's CLAUDE.md.
