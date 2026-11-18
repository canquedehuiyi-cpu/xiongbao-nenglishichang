# 安装说明 · Skill技能搭建专家

## 方式一：技能市场一键安装（推荐）
1. 打开你所用平台的技能市场（如你正在使用的技能分发中心或智能体工作台技能广场），搜索「Skill技能搭建专家」。
2. 订阅 / 安装，即装即用。

## 方式二：zip 手动安装
1. 从发布处下载 `skill-builder-expert.zip`。
2. 打开你所用的智能体平台（支持上传技能的平台均可）。
3. 找「技能」入口 → 上传 zip → 验证触发词（回「做技能Skill」或「技能搭建开工」）。

## 装好之后怎么用（四大闭环入口）
- **做技能Skill / 开新技能 / 技能搭建开工** → 进链路1（从零代制作）
- **技能怎么做 / 技能规范 / 收费技能怎么配 / API模式怎么配** → 进链路2（答疑教学）
- **修复技能 / 技能卡住了** → 进链路3（半成品修复）
- **评测技能 / 技能质检** → 进链路4（成品评测）

需求说不清时，专家会按立项表单逐项问你最关键的 1–2 项，补齐后回主线。

## 排障
- **触发词没反应**：确认 zip 内顶层目录名＝`name`＝`slug`（三者一致）；SKILL.md 的 `frontmatter` 闭合完整（两个 `---`）。
- **装配报错 CRLF**：用 `python scripts/package_zip.py <目录>` 会提示哪个文件是 CRLF，改回 LF 再打。
- **自检 FAIL**：按 `scripts/selfcheck_factory.py` 输出的事项清单逐条修，回到修正引擎复检。

## 本包自身装配（开发者用）
```bash
python scripts/package_check.py skill-builder-expert
python scripts/stamp_signature.py skill-builder-expert
python scripts/package_zip.py skill-builder-expert -o skill-builder-expert.zip --mtime fixed
```
