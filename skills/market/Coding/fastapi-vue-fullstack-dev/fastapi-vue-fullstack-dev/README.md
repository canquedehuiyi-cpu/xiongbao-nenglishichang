# fastapi-vue-fullstack-dev

轻量全栈项目标准化开发 Skill：覆盖 **FastAPI 后端 + Vue3 CDN 前端 + SQLite/Alembic 数据库 + Docker 容器化 + 生产部署** 的完整开发链路（需求分析 → 架构设计 → 编码 → 安全加固 → 测试 → 部署上线）。

内容全部沉淀自真实项目的实践与踩坑复盘（含生产部署事故），可直接作为 AI 编码代理（Qoder 等）的 Agent Skill 使用，也可当作团队开发规范手册人工查阅。

## 适用场景

- 新建或迭代 FastAPI / Vue3 / SQLite 技术栈的 Web 项目
- 设计防御式数据库迁移（Alembic）
- 编写增量部署脚本、生产发布
- 安全加固审计、权限管理、数据验证
- 中小型单机部署项目（SQLite + 单容器）；若上 PostgreSQL/K8s，流程思想仍适用但模板需替换

## 项目结构

```
fastapi-vue-fullstack-dev/
├── SKILL.md              # 主入口：8 阶段开发流程检查单 + 常见陷阱速查表
├── prompts.md            # 7 类环节提示词模板（九段式需求/迁移/安全审计/部署/测试/修复/前端）
├── best-practices.md     # 最佳实践：密钥三级策略、权限注入、时间处理、上传安全等
├── deployment.md         # 部署手册：脚本设计原则、部署检查单、回滚预案、故障排查表
└── templates/            # 可直接拷贝使用的配置模板（占位符已通用化）
    ├── Dockerfile.template            # 非 root 运行 + 镜像层缓存 + 自动迁移
    ├── docker-entrypoint.sh.template  # 属主自愈 + setpriv 降权
    ├── docker-compose.yml.template    # 命名卷 + 密钥强制注入 + healthcheck
    ├── config.py.template             # 环境变量收口 + 密钥三级策略
    ├── migrate.py.template            # 三场景防御式迁移 + WAL 一致性备份
    ├── deploy.sh.template             # systemd 感知的增量部署脚本骨架
    └── gitignore.template             # 密钥/数据库/上传文件全覆盖
```

## 作为 Agent Skill 安装（Qoder）

```bash
# 个人级（所有项目生效）
git clone https://github.com/onebody/fastapi-vue-fullstack-dev.git \
  ~/.qoder/skills/fastapi-vue-fullstack-dev

# 或项目级（随仓库分发给团队）
git clone https://github.com/onebody/fastapi-vue-fullstack-dev.git \
  <你的项目>/.qoder/skills/fastapi-vue-fullstack-dev
```

安装后无需其他配置，两种触发方式：

- **自动触发**：对话中提到"新建 FastAPI 项目 / 数据库迁移 / 部署脚本 / 安全加固"等场景时自动加载
- **显式调用**：`/fastapi-vue-fullstack-dev <你的任务>`

## 手动使用模板（不依赖 AI 工具）

```bash
cp templates/Dockerfile.template   你的项目/Dockerfile
cp templates/gitignore.template    你的项目/.gitignore
cp templates/deploy.sh.template    你的项目/scripts/deploy.sh
```

占位符替换规则：`myapp` → 你的应用名，`APP_SECRET` → 你的密钥环境变量名，`{占位符}` → 实际内容。

`prompts.md` 中的提示词模板填好占位符后，可直接作为需求文档发给任何 AI 编码工具。

## 安全说明

- 全部内容已去敏感化：不含任何真实 IP、密码、密钥、用户路径
- 凭据一律通过环境变量注入（如 `DEPLOY_SSH_PASS`、`APP_SECRET:?` 强制校验）
- `gitignore.template` 默认拦截 `*.db` / `.secret_key` / `.env*` / `uploads/` / 备份目录

## 文档导航

| 想做什么 | 看哪里 |
|---------|--------|
| 了解完整开发流程 | `SKILL.md`（8 阶段检查单） |
| 写需求文档 / 给 AI 提任务 | `prompts.md` 对应环节模板 |
| 编码时查规范 | `best-practices.md` |
| 部署前检查 / 部署出故障 | `deployment.md`（检查单 + 故障排查表） |
| 起新项目 | 直接拷 `templates/` |
