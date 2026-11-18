# User Preferences & Scoring Criteria

This file defines the user's project preferences and scoring standards.
WorkBuddy reads this file at the start of each session to align search and evaluation behavior.

---

## Project Interests

The user does not restrict to a fixed domain. Project topics are specified at query time.
When the user provides keywords or topics, use them directly. When the user provides only
a vague description, infer appropriate GitHub search terms and confirm with the user.

### Common Topics (for reference, not exhaustive)

- LLM, AI, machine learning tools and frameworks
- DevOps, Docker, Kubernetes, cloud native
- Web frameworks, frontend, backend
- CLI tools, productivity utilities
- Data engineering, ETL, pipelines
- Security, cryptography, authentication

---

## Scoring Dimensions

Each project is evaluated on the following four dimensions (1-10 scale).

### 1. Innovation (创新性)

- **9-10**: Proposes a fundamentally new paradigm, approach, or solves a novel problem.
- **7-8**: Introduces meaningful new features or significant extension of existing work.
- **5-6**: Incremental improvement or novel combination of existing techniques.
- **3-4**: Minor variation on well-explored ideas.
- **1-2**: No discernible novelty; purely derivative.

### 2. Popularity (热度)

- **9-10**: 10k+ stars with strong growth trajectory, active community.
- **7-8**: 1k-10k stars, established user base, steady growth.
- **5-6**: 100-1k stars, growing adoption.
- **3-4**: <100 stars, limited visibility.
- **1-2**: Abandoned or dormant projects.

### 3. Practicality (实用性)

- **9-10**: Production-ready, excellent documentation, clear use cases, can be adopted directly.
- **7-8**: Well-documented, sufficient detail for implementation, usable with minor effort.
- **5-6**: Basic documentation, requires significant adaptation.
- **3-4**: Limited documentation, mainly for experts.
- **1-2**: Poor documentation, experimental or proof-of-concept only.

### 4. Maintenance (活跃度)

- **9-10**: Updated within last week, active issue resolution, regular releases.
- **7-8**: Updated within last month, responsive maintainers.
- **5-6**: Updated within last 6 months, occasional releases.
- **3-4**: Updated within last year, slow issue resolution.
- **1-2**: No updates in over a year, abandoned project.

---

## Weight Configuration

| Dimension     | Weight | Description                          |
|---------------|--------|--------------------------------------|
| Innovation    | 0.30   | Most important: novel contributions  |
| Popularity    | 0.25   | Important: community认可度           |
| Practicality  | 0.30   | Most important: can it be used?      |
| Maintenance   | 0.15   | Supporting: long-term viability      |

**Weighted Score** = Innovation * 0.30 + Popularity * 0.25 + Practicality * 0.30 + Maintenance * 0.15

---

## Passing Threshold

- **Pass**: Weighted Score >= **6.5**
- **Borderline**: 5.5 <= Weighted Score < 6.5 (flag for user review)
- **Fail**: Weighted Score < 5.5

Only projects with **Pass** status are recorded in `references/rated_projects.md`.
Borderline projects are presented to the user for manual decision.

---

## Customization

The user may adjust any of the following at any time:

1. Add or remove scoring dimensions
2. Change dimension weights (must sum to 1.0)
3. Adjust the passing threshold
4. Add fixed project topics for default searches
5. Add exclusion rules (e.g., "ignore archived projects" or "skip projects without README")

When the user requests a change, update this file immediately and confirm the update.

---

## Output Format (输出格式)

所有搜索评分结果必须使用中文表头呈现：

| # | 项目 | 语言 | Stars | 综合分 | 创新 | 热度 | 实用 | 活跃 | 状态 |
|---|------|------|-------|--------|------|------|------|------|------|
| 1 | owner/repo | Python | 12.5k | 7.8 | 8 | 9 | 7 | 7 | PASS |

说明：创新=Innovation, 热度=Popularity, 实用=Practicality, 活跃=Maintenance
