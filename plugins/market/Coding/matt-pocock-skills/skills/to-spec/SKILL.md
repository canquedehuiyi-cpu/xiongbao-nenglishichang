---
name: to-spec
description: "将当前对话转化为 spec 并发布到项目 issue tracker：不做访谈，只综合你们已经讨论的内容。 Turn the current conversation into a spec and publish it to the project issue tracker: no interview, just synthesis of what you've already discussed."
descriptionZh: '将当前对话转化为 spec 并发布到项目 issue tracker：不做访谈，只综合你们已经讨论的内容。'
---

This skill takes the current conversation context and codebase understanding and produces a spec. Do NOT interview the user; just synthesize what you already know.

The issue tracker and triage label vocabulary should have been provided to you. If not, tell the user to run `/setup-matt-pocock-skills`.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the spec, and respect any ADRs in the area you're touching.

2. Sketch out the seams at which you're going to test the feature. Existing seams should be preferred to new ones. Use the highest seam possible. If new seams are needed, propose them at the highest point you can. The fewer seams across the codebase, the better - the ideal number is one.

Check with the user that these seams match their expectations.

3. Write the spec using the template below, then publish it to the project issue tracker. Apply the `ready-for-agent` triage label - no need for additional triage.

<spec-template>

## 问题陈述

The problem that the user is facing, from the user's perspective.

## 解决方案

The solution to the problem, from the user's perspective.

## 用户故事

A LONG, numbered list of user stories. Each user story should be in the format of:

1. 作为<角色>，我想要<功能>，以便<收益>

<user-story-example>
1. 作为手机银行客户，我想要查看各个账户的余额，以便对支出做出更明智的决策
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## 实现决策

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits.

## 测试决策

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## 超出范围

A description of the things that are out of scope for this spec.

## 补充说明

Any further notes about the feature.

</spec-template>
