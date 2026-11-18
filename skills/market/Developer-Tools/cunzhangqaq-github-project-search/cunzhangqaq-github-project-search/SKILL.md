---
name: 开源项目评分器
description: >
  Search, score, and track GitHub open source projects based on user-defined preferences
  and multi-dimensional scoring criteria. This skill should be used when the user wants to
  find and evaluate GitHub repositories, track interesting projects, or maintain a curated
  list of quality open source projects with filtering. Triggers include: searching GitHub projects,
  rating GitHub repos, finding top projects, project recommendations, GitHub trending analysis,
  or any mention of GitHub repositories with quality filtering intent.
agent_created: true
---

# 开源项目评分器

Search, evaluate, and curate GitHub open source projects with personalized scoring and deduplication.

## Overview

This skill extends basic GitHub search with a structured evaluation pipeline: user preferences
define scoring criteria, each project is scored across multiple dimensions, and only projects
meeting the threshold are recorded — with deduplication to avoid revisiting previously
rated projects.

## Core Capabilities

### 1. Preference Management

Read `references/preferences.md` at the start of each session. This file contains:

- Project interest areas (or instructions to use per-query topics)
- Scoring dimensions (Innovation, Popularity, Code Quality, Maintenance)
- Dimension weights and passing threshold
- Customization rules

When the user requests changes to preferences (e.g., "add a dimension", "change the
threshold", "adjust weights"), update `references/preferences.md` immediately and confirm.

### 2. Project Search

Use `scripts/search_github.js` to query the GitHub API:

```bash
# Flag-based interface (recommended)
scripts/search_github.js -q "<query>" [-n max_results] [-l language] [-s sort] [--date-from YYYY-MM-DD]

# Examples:
scripts/search_github.js -q "LLM inference optimization" -n 10 -l python
scripts/search_github.js -q "web framework" -n 20 -l javascript -s stars
scripts/search_github.js -q "docker kubernetes" -n 15
```

**Flag arguments:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--query` | `-q` | (required) | Search keywords |
| `--max-results` | `-n` | 10 | Number of results to return |
| `--language` | `-l` | none | Programming language filter, e.g. python, javascript, go, rust |
| `--sort` | `-s` | stars | Sort by: stars, updated, created |
| `--date-from` | — | none | Filter repos pushed/updated after this date |

Parse the returned JSON. Each repository contains `full_name`, `description`, `stargazers_count`,
`fork_count`, `language`, `updated_at`, `topics`, and `html_url`.

### 3. Project Scoring

For each project found, perform the following evaluation:

1. **Read the project info** (name, description, topics)
2. **Check deduplication**: Search `references/rated_projects.md` for the project's
   GitHub ID (full_name). If found, skip and note as duplicate.
3. **Score each dimension** (1-10) per the rubric in `references/preferences.md`:
   - Innovation (创新性) — 是否提出新思路或独特解决方案
   - Popularity (热度) — stars、fork数量及增长趋势
   - Practicality (实用性) — 文档完善度、使用场景、能否直接采用
   - Maintenance (活跃度) — 最近更新时间、Issue处理速度、社区活跃度
4. **Calculate weighted score** using the weights from preferences
5. **Determine status**:
   - **Pass**: Weighted Score >= threshold (default 6.5)
   - **Borderline**: Within 1.0 point below threshold
   - **Fail**: Below borderline range

### 4. Record Keeping

For projects that **pass** the scoring threshold, append an entry to
`references/rated_projects.md` using this format:

```markdown
### [SCORE] GitHub_ID - PROJECT_NAME
- **Author**: owner/repo
- **Language**: Primary language
- **Stars**: NNNNN
- **Rated**: YYYY-MM-DD
- **Link**: https://github.com/owner/repo
- **Scores**: Innovation=N Popularity=N Practicality=N Maintenance=N
- **Weighted**: N.NN
- **Keywords**: topic1, topic2
- **Summary**: One-sentence summary.
```

**Deduplication**: Before scoring any project, check `references/rated_projects.md`
for an existing entry with the same GitHub ID (owner/repo). If found, skip the project and inform
the user it was previously rated.

## Workflow

### Standard Search & Rate Workflow

1. Read `references/preferences.md` to load current preferences and scoring criteria
2. Read `references/rated_projects.md` to load previously rated project IDs
3. Accept user's search topic/keywords (or use default interests from preferences)
4. Run `scripts/search_github.js -q "<query>" -n <count> [-l language]`
5. Parse JSON results, extract project entries
6. For each project:
   a. Extract GitHub ID from full_name
   b. Check deduplication against `references/rated_projects.md`
   c. If duplicate, skip and note
   d. If new, score across all dimensions
   e. Calculate weighted score
   f. Determine pass/borderline/fail status
7. Present results to the user in a structured table:
   - Project name, language, stars, weighted score, dimension scores, status
   - Highlight passed projects, flag borderline ones
8. For passed projects, append entries to `references/rated_projects.md`
9. Optionally provide a brief analysis of the batch results

### Preference Update Workflow

When the user requests preference changes:

1. Read current `references/preferences.md`
2. Apply the requested changes
3. Write updated `references/preferences.md`
4. Confirm the changes to the user

### History Review Workflow

When the user wants to review previously rated projects:

1. Read `references/rated_projects.md`
2. Present the entries, optionally filtered by keyword, language, or score range

## Output Format

Present search results in a clear table (must use Chinese table headers):

| # | 项目 | 语言 | Stars | 综合分 | 创新 | 热度 | 实用 | 活跃 | 状态 |
|---|------|------|-------|--------|------|------|------|------|------|
| 1 | owner/repo | Python | 12.5k | 7.8 | 8 | 9 | 7 | 7 | PASS |
| 2 | owner/repo2 | Go | 3.2k | 6.2 | 7 | 6 | 6 | 5 | BORDERLINE |

说明：创新=Innovation, 热度=Popularity, 实用=Practicality, 活跃=Maintenance

For each passed project, also provide a 2-3 sentence summary explaining why it passed
and what makes it noteworthy.

## Examples

- "帮我搜一下最近热门的 LLM 推理优化开源项目，按我的标准评分"
- "Search GitHub for Docker Kubernetes tools, score and filter the results"
- "查看我之前评过的项目"
- "把评分阈值调到 7.0"
- "给热度维度加大权重到 0.35"
- "今天有什么值得关注的 Python 开源项目吗？"

## Resources

- `scripts/search_github.js`: GitHub API search script with language and sort support
- `references/preferences.md`: User preferences, scoring dimensions, weights, and threshold
- `references/rated_projects.md`: Record of previously rated projects for deduplication
