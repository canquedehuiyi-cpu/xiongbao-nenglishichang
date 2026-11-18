---
name: skill-solution-scenic-generator
description:
  这是一个面向支付宝阿宝的 Skill 自动化生产工具。通过交互式引导，帮助开发者快速选择行业模板（当前支持景区购票、茶饮取餐、快餐点单等场景，架构支持灵活扩展更多行业），收集品牌专属配置参数后，自动生成符合规范的品牌定制化 Skill文件。生成产物可直接写入指定目录，并支持一键同步至 AI 能力中心，通过 createSkillAbility 或 updateSkillAbility 接口完成 Skill 的创建、更新与发布，实现从配置到投放的完整闭环。
---

## 文件结构

| 文件 | 职责 |
|---|---|
| `SKILL.md` | 主编排 Skill，流程路由与全局规则（即本文件，含模板扩展附录） |
| `scenic-references/mcp-methods.md` | **唯一接口参考**：全部 MCP 方法 schema + 合约查询 + 文件上传 + 同步入参规则 |
| `scenic-scripts/common.py` | 公共工具（load_json/load_text/find_template_dir/emit_*） |
| `scenic-scripts/validate.py` | 步骤9 参数校验（读取 `--template-detail`） |
| `scenic-scripts/generate.py` | 步骤11 生成+检查+输出（占位符替换+CLIP裁剪+扫描+写入） |
| `scenic-scripts/package.py` | 步骤14-A 打包 |
| `scenic-scripts/to_config_param.py` | 步骤14-B' 组装 configParamList |
| `scenic-scripts/cleanup.py` | 步骤14-E 清理 dist 临时产物 |
| `scenic-templates/jinni/{industryCode}/{sceneCode}/` | 行业场景模板（template.json + .md） |
| `dist/run/template_detail.json` | 运行时生成（不入库），queryTemplateDetail 返回 data，参数定义唯一权威 |
| `../skill-abilities/{abilityEnName}.json`（或 `$SKILL_ABILITIES_DIR`） | 持久能力档案：步骤14-D 写入，供后续查询/撤销/更新 |

## 前置命令规范

1. 统一使用 `alipay-cli`：先检查安装→检查登录→未登录则执行登录
2. 依赖 `python3`（脚本执行 + 浏览器打开），未安装则经用户同意后帮助安装

```bash
# 登录（必须携带 --scope）
alipay-cli login --non-interactive --scope "skill:all,app:all,space:read,ar:read" --json 2>&1
# 用户浏览器授权后确认
alipay-cli login --complete --json 2>&1
```

## 核心规则（最高优先级）

1. **MCP 返回为唯一权威**：模板列表/详情必须调 MCP 获取，禁止臆造。`queryTemplateDetail` 返回 `data` 落盘为 `dist/run/template_detail.json`，步骤9/11 脚本经 `--template-detail` 读取
2. **脚本不可绕过**：主流程每步必须调对应 Python 脚本，stdout JSON 为唯一权威，按 `status` 决定是否继续
3. **失败即中断**：步骤9（validate）和步骤11（generate）失败即终止，不可跳过
4. **工作目录**：执行脚本前先 `cd` 到 SKILL.md 所在目录。中间产物→`dist/run/`，最终产物→`dist/output/skills/`，zip→`dist/output/`，**`dist/` 为可再生临时产物**（步骤14-E 清理）。持久能力档案在 skill 包外（`SKILL_ABILITIES_DIR` 或 `../skill-abilities/`），**禁止清理**
5. **workSpaceId 必经门禁**：步骤2 选定后不变，步骤14-C 使用，不再重复收集
6. **步骤14-16 后置**：需步骤11 产物写入成功 + 用户确认"同步"后进入；**步骤15 预览为必选项**（14 成功后必须进入，生成前先提示用户）；步骤16 审核前必须完成步骤15
7. **修改参数**：如果最终产物已经生成，用户修改了`交互式补参`中的任意参数，需要从 步骤5 重新执行，然后再生成产物。

> **浏览器打开规范**：本 skill 用 `python3 -c "import webbrowser; webbrowser.open('<URL>')"` 打开链接（步骤1 白名单申请链接、步骤15 预览二维码），失败则回退展示链接文本，不阻塞流程。

---

## 执行流程

### 步骤1：白名单校验（必经前置门禁）

调 `skill-template-mcp.checkTemplateWhitelist`（基于 MCP 身份上下文 OID，无需入参）。

- `whitelistPassed=true` → 步骤2
- `whitelistPassed=false` 或 `resultCode != "SUCCESS"` → 展示 `reason`/`applyGuidance`，提供申请链接 `https://open.alipay.com/ai/ai-resource-center/beta-application`，询问是否打开。用户确认 → 按上文浏览器规范打开；拒绝 → 仅展示链接。完成后中断，告知用户通过后重新发起流程从步骤1 开始

### 步骤2：选择工作空间（必经前置门禁）

调 `space-query-service.query-space-list`，按以下逻辑处理：

- **仅 1 个空间** → 默认选定，告知用户后进入步骤3
- **大于 1 个空间** → 列出全部空间供用户选择；若存在默认空间，先询问是否直接使用，用户确认则选定，拒绝则从列表另选

选定后记录 `workSpaceId`，一经选定不变。未选定不得进入后续步骤。

### 步骤3：展示可选模板

调 `skill-template-mcp.querySelectableTemplates` 获取全部可选模板，原样展示。每模板展示：序号、模板编码、模板名称、模板说明、版本、行业/场景、介绍文档。记录 `industryCode`/`sceneCode` 备用。

### 步骤4：用户选定模板

用户在步骤3 列表中选定一个模板，记录 `templateCode` + `templateVersion`。拒绝/取消 → 中断。

### 步骤5：查询模板详情与参数定义

用步骤4 选定的 `templateCode` + `templateVersion` 调 `skill-template-mcp.queryTemplateDetail`，获取完整参数定义。将返回 `data` 落盘为 `dist/run/template_detail.json`。

提取并固化以下字段供步骤7 与主流程使用：
- `industryCode` / `sceneCode` / `templateCode` / `templateVersion`
- 参数清单：`globalParamList`（GLOBAL）、`mcpServerParamList`（MCP_SERVER）、`mcpToolList`（MCP_TOOL）

> 本地 `scenic-templates/jinni/{industryCode}/{sceneCode}/` 仅用于定位 `.md` 模板文件。若本地目录缺失文件，需在步骤7 之前提示中断。

### 步骤6：产品签约预检（不阻断流程）

用 `webFetch` 抓取步骤5 返回的 `introUrl` 文档，提取前台产品码（`salesProductCode`），调 `ar-query.queryArInfosBySalesProd` 批量查询签约状态。

- `data.arInfoList` 非空 → 已签约；为空 → 未签约
- 抓取/调用/识别失败 → 记 warning 并跳过，**不阻断**，进入步骤7
- 存在未签约产品 → 提示用户（不中断），进入步骤7

### 步骤7：交互式补参

基于步骤5 参数清单，一次性向用户展示全部待填参数，**每个参数完整展示**：`paramLabel`、`description`、**`purpose`（参数用途，优先于 description）**、`example`、`defaultValue`、`required`。

**示例格式一致性校验（必做）**：对有 `example` 的参数，收到输入后按结构特征比对（协议前缀、分隔符、appId 段、纯数字、URL 形态等），非逐字符比对。格式不符 → 必须提示用户不一致点 + 期望格式 + 请确认或修正。仅比格式不强制值内容。若有 `validationType`/`validationRule`，叠加执行。

**可查询字段自动发现**：收集任一参数前，先查 `mcp-methods.md` 接口索引；若存在能查回候选值的接口，先调它获取列表让用户选定再回填。已知：`miniAppAppId`（查小程序列表）、`mcpPrefix`（查 MCP 能力，回填 `serverDiscoveryCode`）。`workSpaceId` 已在步骤2 选定，不再收集。

**MCP 能力必检与空阻断**：收集 `mcpPrefix` 前先调 `ability-query-mcp.pageQueryMcpAbility`（`ownerCode` 取当前用户 OID、`ownerType=OID`）。返回为空 → **阻断流程**，引导用户先开发并上线 MCP 服务（提供 `introUrl` 引导），上线后重新发起。非空 → 展示供选定（`abilityCnName`/`abilityEnName`/`abilityStatus`/`serverDiscoveryCode`/`abilityDesc`），选定后 `mcpPrefix` 取 `serverDiscoveryCode`。

**收集规则**：
- GLOBAL：收集 `paramName → paramValue`，必填项不可为空，做示例格式校验
- MCP_SERVER：收集 `mcpPrefix`，**取值 = `serverDiscoveryCode`（非 `abilityEnName`）**；

同时确认操作类型：`action=create`（新建）或 `action=update`（更新，需询问原 `abilityEnName`）。

### 步骤8：组装 bizParam 并进入主流程

把步骤7 收集到的参数按 `paramType` 组装成 bizParam 数组：

```json
[
  {"paramType":"GLOBAL","paramName":"<ParamVO.paramName>","paramValue":"<步骤7 收集值>"},
  {"paramType":"MCP_SERVER","paramName":"<ParamVO.paramName>","paramValue":"<步骤7 收集值>"},
  {"paramType":"MCP_TOOL","paramName":"<McpToolVO.toolName>","paramValue":"<步骤7 收集值>"}
]
```

`paramName` 口径：GLOBAL/MCP_SERVER 取 `ParamVO.paramName`，MCP_TOOL 取 `McpToolVO.toolName`。未提供的项由 validate.py 自动补全。

**直传触发校验**：直传跳过准备阶段时，入参须满足：`workSpaceId` 非空（否则回退步骤2）、`templateCode`/`templateVersion`/`industryCode`/`sceneCode` 非空、bizParam 覆盖全部必填 GLOBAL 参数、`dist/run/template_detail.json` 存在（否则步骤9 自动补调 `queryTemplateDetail` 落盘）。校验通过 → 步骤9；不通过 → 转交互式从步骤3 开始。

---

## 主流程

> 步骤9-11 不可变更顺序。执行前先 `cd` 到 SKILL.md 所在目录。

### 步骤9：参数校验（validate.py）

直接传入步骤8 组装的 bizParam JSON 数组，validate.py 内部按 `paramType` 构建 config 并校验：

| paramType | 转换规则 |
|-----------|---------|
| GLOBAL | config.global.{paramName} = paramValue |
| MCP_SERVER | config.mcp.server.{paramName} = paramValue |
| MCP_TOOL | config.mcp.tools 中 name==paramName 的项设 value=paramValue |
| SWITCH | config.switches.{paramName} = paramValue（"true"/"false"→boolean） |

未提供的项由 validate.py 自动填充默认值（GLOBAL 取 `defaultValue`，MCP_TOOL 取 `toolName`，MCP_SERVER.transport 取 `Streamable HTTP`）。

```bash
python3 scenic-scripts/validate.py \
  --biz-param '<步骤8 bizParam JSON 数组>' \
  --template-detail dist/run/template_detail.json \
  --templates-dir scenic-templates/jinni/ \
  --industry-code {industryCode} \
  --scene-code {sceneCode}
# → 默认输出 dist/run/validated_config.json
```

- status=error → 中断，返回缺失/错误字段列表
- status=success → 步骤10

### 步骤10：确认规划

向用户展示规划方案并确认：

- action=create：AI 生成 abilityEnName，格式 `{品牌英文名/拼音}-{sceneCode小写}-{yyyyMMddHHmmss}`（执行 `python3 -c "from datetime import datetime; print(datetime.now().strftime('%Y%m%d%H%M%S'))"` 获取时间戳）。**命名铁律：各段只能用连字符 `-`，禁止下划线 `_`**——sceneCode 小写后含下划线须替换为 `-`（如 `TICKET_BOOKING` → `ticket-booking`），最终名称不得出现任何 `_`
- action=update：使用用户提供的原 abilityEnName，检查 `{output-dir}/{abilityEnName}/SKILL.md` 是否存在，不存在则中断

| 规划项 | 内容 |
|--------|------|
| 操作类型 | 新建 / 更新 |
| Skill 名称 | abilityEnName |
| description | 功能描述 + 触发条件 |

用户确认 → 步骤11；拒绝 → 中断。

### 步骤11：生成+检查+输出（generate.py）

一步完成占位符替换 + CLIP 裁剪 + 未替换占位符扫描 + 产物写入。

```bash
python3 scenic-scripts/generate.py \
  --industry-code {industryCode} \
  --scene-code {sceneCode} \
  --templates-dir scenic-templates/jinni/ \
  --config dist/run/validated_config.json \
  --template-detail dist/run/template_detail.json \
  --ability-en-name {abilityEnName}
# → 直接输出 dist/output/skills/{abilityEnName}/SKILL.md
```

- status=error → 中断，返回模板/裁剪/替换/写入错误
- status=warning → 产物已写入，但存在未替换占位符或 MCP 格式异常（不阻塞，记录 warning）
- status=success → 步骤14（可选）

> 步骤9-11 主流程到此结束。步骤14-16 为后置环节。

---

### 步骤14：同步 AI 能力中心（可选后置）

步骤11 产物写入成功后，询问用户是否同步。用户确认 → 执行：

1. **14-A 打包**：`scenic-scripts/package.py` 将产物打包为 zip
2. **14-B 上传 zip**：`alipay-cli file upload`，取返回 `fileKey` 作为 `fileId`（详见 `mcp-methods.md`「文件上传与同步辅助」）
3. **14-B' 组装入参**：由 `scenic-scripts/to_config_param.py` 自动组装 `configParamList`（仅 GLOBAL+MCP_SERVER，排除 MCP_TOOL），结果通过 stdout 输出。`mcpRelList` 取步骤7 所选条的 `abilityCode`+`serverDiscoveryCode`。组装完整 MCP 入参，向用户**仅展示**以下字段确认：`abilityEnName`/`abilityCnName`（标注 `[推荐]` 可改）/`abilityDesc`（标注 `[自动填]`）/`iconFileId`/`workSpaceId`（回显）；`configParamList`/`createSource`/`fileId`/`templateCode`/`templateVersion`/`mcpRelList` 为自动填入，**不展示给用户**。用户 Confirm 后进入 14-C
4. **14-C 调用 MCP**：`alipay-cli mcp call`，按 action + 目标能力状态路由（详见 `mcp-methods.md`「update 铁律」）：
   - `action=create` → `skill-config-mcp.createSkillAbility`
   - `action=update` 且 `abilityStatus ∈ {DEV, PRE}` → `updateSkillAbility`（同版本就地改）
   - `action=update` 且 `abilityStatus ∈ {ONLINE, GRAY}` → 先 `upgradeSkillAbility` 派生新版本，再 `updateSkillAbility` 写新版本
   - `auditStatus=AUDITING` → 先 `cancelAuditTask` 撤审，再按上面规则走
5. **14-D 记录能力档案（必做）**：14-C 返回 `SUCCESS` 后，写入**持久档案** `{abilities_dir}/{abilityEnName}.json`（`abilities_dir` = `$SKILL_ABILITIES_DIR` 或 `../skill-abilities/`）。字段：`abilityCode`/`abilityVersion`（取 14-C 返回 data）、`abilityEnName`/`abilityCnName`、`workSpaceId`/`workSpaceName`、`templateCode`/`templateVersion`/`industryCode`/`sceneCode`、`createSource`/`fileId`/`mcpRelList`、`snapshot`（调 `queryMySkill` 取 `abilityStatus`/`abaoStatus`/`auditStatus`）、`audit`（步骤16 成功后记 `reviewId`+`auditStatus`+`submitted:true`）、`recordedAt`。`action=update` 成功则更新同 `abilityEnName` 档案，不新建文件
6. **14-E 清理临时产物（必做，14-D 之后）**：调 `scenic-scripts/cleanup.py` 清理 `dist/` 下全部临时产物。**仅清理 `dist/`**，不触碰持久能力档案。提示用户"临时产物已清理"

> **硬约束**：`configParamList` + `mcpRelList` 必传不得降级；`fileId` = 14-B fileKey；update 须带 `abilityCode` + `abilityVersion`；14-C 成功后必须执行 14-D 写档案 + 14-E 清理 dist。任一子步骤失败仅中断步骤14。

### 步骤15：预览（必选，步骤14 成功后）

> **必选项**：步骤14 同步成功后预览为必做环节，不得跳过。**生成前必须先提示用户**——说明即将生成预览二维码、预览目的（扫码体验已同步的 Skill）、二维码时效较短（约 5 分钟），待用户确认后调 `composePreviewQrCode`。用户仅可在"提示确认"环节暂缓（停在步骤15 入口），但进入步骤16 审核前必须先完成预览。

用户确认 → 调 `skill-config-mcp.composePreviewQrCode`，传入 14-C 返回的 `abilityCode` + `abilityVersion`：

```bash
alipay-cli mcp call skill-config-mcp.composePreviewQrCode \
  -d '{"request":{"abilityCode":"{abilityCode}","abilityVersion":"{abilityVersion}"}}' \
  --json 2>/dev/null
```

- `resultCode=SUCCESS` → 取可用预览链接（优先级 `qrCodeUrl` > `previewUrl` > `dynamicImgUrl`），**立即用浏览器规范自动打开**，同时展示链接文本。`expireAt` 换算为本地可读时间展示，过期则重新调用
- `resultCode != SUCCESS` → 提示错误，不阻塞流程

> 预览不影响能力状态，可反复调用。步骤14-E 已清理 dist 不影响预览——预览基于服务端已同步的能力，数据取自持久能力档案。

### 步骤16：提交审核（可选，步骤15 预览后）

**前置：步骤15 预览已完成**（未预览不得提交审核）。

用户确认 → 调 `ability-task-mcp.createAuditTask`，传入 `abilityCode` + `abilityVersion`：

```bash
alipay-cli mcp call ability-task-mcp.createAuditTask \
  -d '{"request":{"abilityCode":"{abilityCode}","abilityVersion":"{abilityVersion}","abilityType":"SKILL"}}' \
  --json 2>/dev/null
```

- `resultCode=SUCCESS` → 能力进入审核中（`auditStatus=AUDITING`），取 `data.reviewId`
- `resultCode != SUCCESS` → 提示错误，不阻塞已同步的能力

**更新能力档案（必做）**：审核成功后更新持久档案 `audit` 字段（`reviewId`/`auditStatus`/`submitted:true`/`submittedAt`），调 `queryMySkill` 刷新 `snapshot`。

> 审核结果需人工在审批平台处理。用户可随时要求查审核状态（`queryMySkill` → `auditStatus`）或撤销审核（`cancelAuditTask`）。
> **查询/预览/撤销/更新能力**：上下文明确 → 直接用；不明确 → 读能力档案目录全部 `*.json` 列出让用户选。定位后按需调 `queryMySkill`/`composePreviewQrCode`/`createAuditTask`/`cancelAuditTask`/`updateSkillAbility`。
> **流程结束输出规范**：全流程完成或中断后，**禁止逐步骤回顾**（不得输出包含全部步骤的回顾表格）。仅简洁汇报最终关键结果：`abilityEnName`/`abilityCnName`/`abilityCode`/`abilityVersion`/`abilityStatus`/`abaoStatus`（+ `auditStatus` 若已提交审核）/ 持久档案路径，以及后续可用操作提示（查审核状态/预览/撤销审核）。**有跳过或警告必须提示**：若执行过程中存在被跳过的步骤（如步骤6 签约预检未通过/未识别）或 warning（如步骤11 未替换占位符），须在最终输出中单独列出这些项及原因，提醒用户关注。

---

## 模板扩展指南

新增行业/场景模板的规范：

### 1. 创建模板目录

在 `scenic-templates/jinni/` 下按 `{industryCode}/{sceneCode}/` 结构创建目录，放入两个文件：

- `template.json`：元信息文件

  | 字段 | 说明 |
  |------|------|
  | `templateCode` | 模板编码（`{INDUSTRY}_{SCENE}` 大写下划线） |
  | `industryCode` | 行业编码（大写英文，如 `SCENIC`、`FASTFOOD`） |
  | `sceneCode` | 场景编码（大写英文，如 `TICKET_BOOKING`） |
  | `industry` | 行业中文名 |
  | `scene` | 场景中文名 |
  | `version` | 模板版本号 |
  | `generatorSkill` | 固定 `skill-solution-scenic-generator` |
  | `skillTemplate` | Skill 模板 .md 文件名（与同目录下 .md 一致） |
  | `whitepaper_url` | 介绍文档 URL |

- `{skillTemplate}.md`：使用 `【{{paramName}}】` 占位符格式

### 2. 占位符规范

`paramName` 必须与服务端 `queryTemplateDetail` 返回的 `paramName` 一一对应：
- **GLOBAL**：如 `【{{scenicAreaName}}】`
- **MCP_SERVER**：如 `【{{mcpPrefix}}】`
- **MCP_TOOL**：如 `【{{searchProducts}}】`
- **特殊**：`【{{skillName}}】`（步骤10 注入，非 bizParam 传入）

### 3. CLIP 裁剪标记（可选）

```markdown
<!-- CLIP:step_xxx START -->
本段内容在对应 switch 关闭时被裁剪
<!-- CLIP:step_xxx END -->
```

> 服务端当前不返回 switches，CLIP/switch 机制为预留死代码，`clip_template` 保留但恒不触发。

### 4. 验证流程

```bash
# 语法检查
python3 -c "import py_compile; py_compile.compile('scenic-scripts/common.py', doraise=True)"
# 模板目录定位测试
python3 -c "import sys; sys.path.insert(0, 'scenic-scripts'); from common import find_template_dir; print(find_template_dir('scenic-templates/jinni/', '{industryCode}', '{sceneCode}'))"
```

确保 `find_template_dir` 能正确定位到新模板目录，且 `template.json` 中 `generatorSkill` 为 `skill-solution-scenic-generator`。
