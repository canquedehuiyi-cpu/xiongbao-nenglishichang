#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 00-总览.md 与 .gitignore；报告来源、规模、许可边界与移植方法。"""
import os, json, csv, datetime

RAW = "D:/workbuddy-market-export/_raw"
OUT = os.environ.get("EXPORT_OUT", "D:/xiongbao-nenglishichang")

summary = json.load(open(os.path.join(RAW, "organize-summary.json"), encoding="utf-8"))
c = summary["counts"]
meta = json.load(open(os.path.join(RAW, "skillhub", "meta_top200.json"), encoding="utf-8"))
cat = json.load(open(os.path.join(RAW, "expert_center.json"), encoding="utf-8"))

missing_avatar = 0
if os.path.isfile(os.path.join(RAW, "failures-experts.json")):
    missing_avatar = len(json.load(open(os.path.join(RAW, "failures-experts.json"), encoding="utf-8")))
sh_missing = 0
for f in ("failures-shdl.json", "skillhub/still-missing.json"):
    p = os.path.join(RAW, f)
    if os.path.isfile(p):
        sh_missing = max(sh_missing, len(json.load(open(p, encoding="utf-8"))))

today = datetime.date.today().isoformat()
txt = """# WorkBuddy 资产全量镜像

> 采集日期：{today}
> 用途：把 WorkBuddy（CodeBuddy）的**专家 / 插件 / 连接器 / 技能**以可直接移植的目录形态归档。
> 本仓库是**第三方资产镜像**，不是 WorkBuddy 官方仓库；各条目版权与许可归原作者所有。

## 一、资产概览

| 分区 | 条目数 | 来源 | 说明 |
|---|---:|---|---|
| `01-专家市场` | {n_expert} | 公开 COS `expert-marketplace` | 429 位专家，按 15 个中文类目归档；含正文与头像 |
| `02-插件市场/连接器` | {n_conn} | 本机 `~/.workbuddy/connectors-marketplace` | 连接器正文（含内置 skills），中文名取自 `connectors.json` |
| `02-插件市场/插件包` | {n_plug} | 本机 `~/.workbuddy/plugins/marketplaces` | 官方 / 团队插件包 |
| `03-技能市场/官方技能` | {n_official} | 公开 CDN `skill-marketplace.zip` | 清单 293 个 + zip 内多出 2 个（weather / westock-data），按中文标签分类 |
| `03-技能市场/内置技能` | {n_builtin} | 本机 `workbuddy-builtin` | WorkBuddy 内置插件/技能（含多版本目录） |
| `03-技能市场/社区技能` | {n_community} | SkillHub 公网 API | 13 个类目 × Top 200，按 slug 去重保下载量最高 |
| `索引` | {n_rows} 行 | 扫描目录生成 | `*.csv` 均为 **UTF-8 BOM**，Excel 可直接打开 |

社区技能采集原始量 {sh_raw} 条，去重后 {sh_dedup} 条；已下载正文 {sh_ok} 条。

## 二、目录约定

每个条目目录内含一份 `说明.md`，字段固定为：

```
- **类目**：…
- **原始标识**：…
## 简介
…
```

索引生成器按这三个字段解析，因此**请勿删除或改字段名**。

## 三、直接移植到你的项目

WorkBuddy / CodeBuddy 按 `<项目>/.workbuddy/skills/<名称>/SKILL.md` 自动发现技能。
社区技能与官方技能的条目目录就是标准 `SKILL.md` 目录，**直接复制**即可：

```bash
# 例：把某个社区技能移植到项目
cp -r "03-技能市场/社区技能/办公效率/腾讯文档/."  <你的项目>/.workbuddy/skills/tencent-docs/
```

也可以用 SkillHub 官方 CLI 按需拉取（无需本仓库）：

```bash
npx @skill-hub/cli install <slug> --dir <你的项目>/.workbuddy/skills -y
# 注意：CLI 走 skillhub.club 注册表，与本站 lightmake.site 中文市场并非同一套；
# 本站条目请优先用上面的「直接复制」方式。
```

专家包（`.tar.gz`）与插件包是完整工程目录，解压后放到对应 markets 目录即可。

## 四、已知缺口

- 专家头像缺失 {miss_avatar} 个：源站对这些 ID 返回 404，正文不受影响。
- 社区技能正文缺失约 {sh_missing} 个：源站 404（技能已下架）或网络 502；`说明.md` 中已标注“仅保留元数据”。
- 单个超过 90 MB 的文件已按 `.part01/.part02…` 切片（GitHub 单文件 100 MB 限制），按序号拼接即可还原：
  `cat file.part* > file` 。

## 五、许可边界（对外分发前必读）

- 这些条目来自公开市场与本机缓存，**每个条目可能带自己的 LICENSE**（插件包见 `.codebuddy-plugin/` 与包内 LICENSE）。
- “金融投资”“商业运营”类目常含**付费/需 API Key** 的技能；`说明.md` 的简介中通常有标注。
- 本仓库仅作**归档与检索**用途；二次发布、商用前请逐条核对原许可。
- 内置技能（`03-技能市场/内置技能`）来自 WorkBuddy 客户端安装目录，可能受软件许可限制，不建议单独再分发。

## 六、再生成

采集与整理脚本保存在 `_raw/scripts/`（`.py`），元数据 JSON 在 `_raw/` 顶层。
重新采集：依次运行 `export_all.py {{experts,official,shmeta,shdl,local,builtin}}` → `organize.py` → `make_overview.py`。
""".format(
    today=today, n_expert=c.get("experts", 0), n_conn=c.get("connectors", 0),
    n_plug=c.get("plugins", 0), n_official=c.get("official", 0),
    n_builtin=c.get("builtin", 0), n_community=c.get("community", 0),
    n_rows=summary["indexRows"], sh_raw=meta["rawCount"], sh_dedup=meta["dedupCount"],
    sh_ok=meta["dedupCount"] - sh_missing, miss_avatar=missing_avatar, sh_missing=sh_missing,
)
open(os.path.join(OUT, "00-总览.md"), "w", encoding="utf-8").write(txt)

# _raw 里的原始压缩包体积巨大且与整理后目录重复；不入库，但保留脚本与元数据以便复现。
keep = {"expert_center.json", "organize-summary.json", "failures-experts.json",
        "failures-shdl.json", "skillhub/meta_top200.json", "skillhub/still-missing.json",
        "local/connectors.json"}
lines = [
    "# 原始二进制压缩包不入库（可整体删除）",
    "_raw/experts/", "_raw/official/", "_raw/skillhub/zips/", "_raw/local/",
    "_raw/cli-test/", "",
    "# 保留脚本与元数据（用于复现与对账）",
    "!_raw/scripts/",
]
open(os.path.join(OUT, ".gitignore"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("[overview] written, keep=%d" % len(keep), flush=True)
