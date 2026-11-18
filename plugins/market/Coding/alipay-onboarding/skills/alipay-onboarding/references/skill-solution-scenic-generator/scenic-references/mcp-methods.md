# MCP 服务概览

| MCP Server | 工具名称 | 工具说明 |
| --- | --- | --- |
| skill-config-mcp | createSkillAbility | 创建 skill |
| skill-config-mcp | updateSkillAbility | 更新 skill |
| skill-config-mcp | upgradeSkillAbility | 升级 skill（派生新版本） |
| skill-config-mcp | deleteSkillAbility | 删除 skill |
| skill-config-mcp | composePreviewQrCode | 预览 skill |
| skill-template-mcp | querySelectableTemplates | 查询可选模板列表 |
| skill-template-mcp | queryTemplateDetail | 查询模板详情 |
| skill-template-mcp | checkTemplateWhitelist | 检查白名单 |
| ability-task-mcp | createAuditTask | 提交审核 |
| ability-task-mcp | cancelAuditTask | 取消审核 |
| ability-query-mcp | pageQueryMcpAbility | 分页查询已上线 MCP 能力 |
| ability-query-mcp | queryMySkill | 查询我的 Skill 详情 |
| ar-query | queryArInfosBySalesProd | 按前台产品码查签约合约 |
| ar-query | queryArInfosByBackProd | 按后台产品码查签约合约 |
| space-query-service | query-space-list | 查询工作空间列表 |
| miniapp-query-tool | query-mini-app-list | 查询小程序列表 |

> **调用方式**：`alipay-cli mcp call {server}.{tool} -d '{...}' --json 2>/dev/null`
> **request 包裹规则**：接收 `XxxRequest` 对象的接口用 `{"request":{...}}` 包裹；接收基本类型（如 `String`）的接口直接传参。
> **成功判定**：`resultCode === "SUCCESS"`；`space-query-service`/`miniapp-query-tool` 响应结构为 `{success, errorContext, resultObj}`，以 `success === true` 判定。
> **参数铁律**：按各方法参数表一字不改执行，不得省略/改名/脑补/改嵌套结构。文档没写的参数不加，文档写了的参数不减。

# 公共结构定义

### ConfigParam
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `paramType` | `String` | 参数类型 |
| `paramName` | `String` | 参数名称 |
| `paramValueType` | `String` | 参数值类型 |
| `paramValue` | `String` | 参数值 |
| `description` | `String` | 参数描述 |
| `sortOrder` | `int` | 排序序号 |

### McpRel
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `mcpAbilityCode` | `String` | MCP 能力编码 |
| `serverDiscoveryCode` | `String` | 服务发现编码 |

### Result\<T\> 响应结构
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `resultCode` | `String` | `SUCCESS` 或具体错误码 |
| `resultMsg` | `String` | 结果描述 |
| `data` | `T` | 业务数据 |

### PreviewFlowStep 结构
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `stepOrder` | `int` | 步骤序号 |
| `stepName` | `String` | 步骤名称 |
| `stepDesc` | `String` | 步骤描述 |

---

# Skill **配置接口** (skill-config-mcp)

## createSkillAbility

### 请求参数 `AlipayCliSkillCreateRequest`
| 字段 | 类型 | 必填 | 说明                     |
| --- | --- | --- |------------------------|
| `abilityEnName` | `String` | 是 | 能力英文名称,名称必须要跟zip包里面的Skill.md中的名字一致                |
| `abilityCnName` | `String` | 是 | 能力中文名称                 |
| `abilityDesc` | `String` | 是 | 能力描述                   |
| `iconFileId` | `String` | 是 | 图标文件ID，参照 # 文件上传与同步辅助(上传返回的 fileKey）) |
| `workSpaceId` | `String` | 是 | 工作空间 ID                |
| `templateCode` | `String` | 是 | 模板编码                   |
| `templateVersion` | `String` | 是 | 模板版本                   |
| `fileId` | `String` | 是 | 文件 ID（上传返回的 fileKey）   |
| `extInfo` | `Map<String, String>` | 否 | 扩展信息                   |
| `mcpRelList` | `List<McpRel>` | 否 | MCP 关联列表               |
| `configParamList` | `List<ConfigParam>` | 否 | 配置参数列表                 |
### 响应 `SkillCreateResultMcpVO`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `abilityCode` | `String` | 能力编码 |
| `abilityVersion` | `String` | 能力版本 |

### 调用示例
```bash
alipay-cli mcp call skill-config-mcp.createSkillAbility \
  -d '{"request":{"abilityEnName":"my_skill","abilityCnName":"我的技能","abilityDesc":"描述","iconFileId":"<fileKey>","workSpaceId":"ws_001","templateCode":"tpl_001","templateVersion":"1.0","fileId":"<fileKey>","configParamList":[{"paramType":"GLOBAL","paramName":"query","paramValueType":"STRING","paramValue":"test","description":"查询参数","sortOrder":1}],"mcpRelList":[{"mcpAbilityCode":"mcp_001","serverDiscoveryCode":"sd_001"}]}}' --json 2>/dev/null
```

## updateSkillAbility

### 请求参数 `AlipayCliSkillUpdateRequest`
| 字段 | 类型 | 必填 | 说明                                 |
| --- | --- | --- |------------------------------------|
| `abilityCode` | `String` | 是 | 能力编码                               |
| `abilityVersion` | `String` | 是 | 能力版本                               |
| `abilityEnName` | `String` | 否 | 能力英文名称，名称必须要跟zip包里面的Skill.md中的名字一致 |
| `abilityCnName` | `String` | 否 | 能力中文名称                             |
| `abilityDesc` | `String` | 否 | 能力描述                               |
| `iconFileId` | `String` | 否 | 图标文件ID，参照 # 文件上传与同步辅助(上传返回的 fileKey）)              |
| `workSpaceId` | `String` | 是 | 工作空间 ID                            |
| `templateCode` | `String` | 否 | 模板编码                               |
| `templateVersion` | `String` | 否 | 模板版本                               |
| `fileId` | `String` | 否 | 文件 ID                              |
| `mcpRelList` | `List<McpRel>` | 否 | MCP 关联列表                           |
| `configParamList` | `List<ConfigParam>` | 否 | 配置参数列表                             |

### 响应
同 `createSkillAbility`。

> **update 铁律**：必填 `abilityCode`+`abilityVersion`（非 abilityEnName）+`workSpaceId`；`update` 前必须先 `queryMySkill` 确认状态再路由：
> - `abilityStatus ∈ {DEV, PRE}`（可编辑态）→ 同版本就地改（`updateSkillAbility`）
> - `abilityStatus ∈ {ONLINE, GRAY}`（已上线/灰度）→ 先 `upgradeSkillAbility` 派生新版本（如 0.0.1→0.0.2），再 `updateSkillAbility` 写新版本
> - `auditStatus=AUDITING`（审核中）→ 先 `cancelAuditTask` 撤审，再按上面规则走

## create/update 字段填入规则（共通）

| 字段 | 来源                                                                       | 必填 |
|------|--------------------------------------------------------------------------|------|
| `fileId` | 上传返回的 `fileKey`，AI 直接回填                                                  | ✅ |
| `abilityEnName` | create 为自动生成值；update 为原值，不可变                                             | create ✅ |
| `abilityCode`/`abilityVersion` | 仅 update：原能力编码+版本，向用户询问或 `queryMySkill` 查得                               | update ✅ |
| `templateCode`/`templateVersion` | 步骤5 已确认值                                                                 | create ✅ |
| `workSpaceId` | 步骤2 已选定值（必经门禁），不再重复收集                                                    | ✅ |
| `abilityCnName` | AI 推荐（基于 brandName+sceneName），标注 `[推荐]` 可改                               | create ✅ |
| `abilityDesc` | 自动取产物 SKILL.md frontmatter `description`，标注 `[自动填]`                      | create ✅ |
| `iconFileId` | 向用户收集 (图标文件上传后返回的 fileKey）                                               | ⬜ |
| `deliveryTargets`/`mcpRelList` | 向用户收集（可用 `template_detail.json` 的 `mcpToolList`/`mcpServerParamList` 辅助） | ⬜ |
| `configParamList` | `to_config_param.py` 自动组装（**仅 GLOBAL+MCP_SERVER，排除 MCP_TOOL**）           | 自动 |

> **mcpPrefix 取值铁律**：`configParamList` 中 `mcpPrefix`（MCP_SERVER）的 `paramValue` = 所选 MCP 能力的 `serverDiscoveryCode`（网关注册编码，形如 `mcp.third.openmcpgw.open.xxx`），与 `mcpRelList[].serverDiscoveryCode` 同源。**禁止用 `abilityEnName`**——服务端按 `MCP[xxx]` 查注册表，用 `abilityEnName` 会报 `MCP[xxx]不存在`。
> **展示约束**：向用户**仅展示**以下字段确认：`abilityEnName`/`abilityCnName`（标注 `[推荐]` 可改）/`abilityDesc`（标注 `[自动填]`）/`iconFileId`/`workSpaceId`（回显）。`configParamList`/`fileId`/`templateCode`/`templateVersion`/`mcpRelList` 为自动填入，**不展示给用户**。不得填占位值。
> **硬约束**：`configParamList` + `mcpRelList` 必传不得降级；`fileId` = 上传 fileKey；update 须带 `abilityCode` + `abilityVersion`。

## upgradeSkillAbility

### 请求参数 `SkillUpgradeMcpRequest`
| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `abilityCode` | `String` | 是 | 能力编码 |
| `abilityVersion` | `String` | 是 | 能力版本 |

响应 `Boolean`：`true` 表示升级成功（派生新版本，新版本为 DEV 态可编辑）。

## deleteSkillAbility

### 请求参数 `SkillDeleteMcpRequest`
| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `abilityCode` | `String` | 是 | 能力编码 |
| `abilityVersion` | `String` | 是 | 能力版本 |

响应 `Boolean`：`true` 表示删除成功。

## composePreviewQrCode

### 请求参数 `PreviewQrCodeRequest`
| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `abilityCode` | `String` | 是 | 能力编码 |
| `abilityVersion` | `String` | 是 | 能力版本 |

> 调试目标账号从 MCP 身份上下文自动获取，无需传入。

### 响应 `PreviewQrCodeMcpVO`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `qrCode` | `String` | 二维码内容（常为 null，不要依赖） |
| `expireAt` | `Date` | 过期时间（毫秒级时间戳，须换算为本地可读时间） |
| `dynamicImgUrl` | `String` | 二维码动图 URL |

> **链接取值优先级**：`qrCodeUrl` > `previewUrl` > `dynamicImgUrl`（`qrCode` 字段常为 null）。拿到后立即用 `python3 -c "import webbrowser; webbrowser.open('<URL>')"` 自动打开。TTL 约 2 分钟，过期则重新调用。

---

# 审核接口 (ability-task-mcp)

## createAuditTask

### 请求参数 `CreateAuditTaskRequest`
| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `abilityCode` | `String` | 是 | 能力编码 |
| `abilityVersion` | `String` | 是 | 能力版本 |
| `abilityType` | `String` | 否 | 能力类型（如 `SKILL`） |
| `belongType` | `String` | 否 | `ANT`/`THIRD_PARTY` |
| `uniqueSuffix` | `String` | 否 | 唯一后缀（重试区分） |
| `skipManagerAudit` | `Boolean` | 否 | 是否跳过主管审核 |

### 响应 `AuditSubmitResultMcpVO`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `reviewId` | `String` | 审核任务标识 |
| `auditStatus` | `String` | 提交成功后为 `AUDITING` |

## cancelAuditTask

### 请求参数 `CancelAuditTaskRequest`
| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `abilityCode` | `String` | 是 | 能力编码 |
| `abilityVersion` | `String` | 是 | 能力版本 |
| `abilityType` | `String` | 否 | 能力类型 |

响应 `Boolean`：`true` 表示取消成功。

---

# 查询接口 (ability-query-mcp)

## pageQueryMcpAbility

### 请求参数 `MerchantMcpPageQueryRequest`
| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `abilityType` | `String` | 否 | 接口内部固定为 `MCP` |
| `workSpaceId` | `String` | 否 | 工作空间 ID |
| `pageNo` | `Integer` | 否 | 默认 `1` |
| `pageSize` | `Integer` | 否 | 默认 `10` |

### 响应 `MerchantMcpVO`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `abilityCode` | `String` | 能力编码（对应 mcpId） |
| `abilityEnName` | `String` | 能力英文名称 |
| `abilityCnName` | `String` | 能力中文名称 |
| `abilityType` | `String` | 协议类型（MCP，仅 A2A） |
| `abilityStatus` | `String` | `DEV`/`PRE`/`AUDIT`/`GRAY`/`ONLINE` |
| `abilityBizStatus` | `String` | 能力业务状态 |
| `abilityVersion` | `String` | 能力版本 |
| `abilityDesc` | `String` | 能力描述 |
| `belongType` | `String` | `ANT`/`THIRD_PARTY` |
| `sourcePlatform` | `String` | 来源平台 |
| `serverDiscoveryCode` | `String` | 服务发现编码（**mcpPrefix 取此值**） |

> **空阻断**：返回列表为空（用户名下无任何 MCP 能力）→ 阻断流程，引导用户先开发并上线品牌 MCP 服务后才能生成 Skill。

## queryMySkill

### 请求参数 `SkillQueryRequest`
| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `abilityCode` | `String` | 是 | 能力编码 |
| `abilityVersion` | `String` | 是 | 能力版本 |

### 响应 `SkillInfoMcpVO`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `abilityCode` | `String` | 能力编码 |
| `abilityVersion` | `String` | 能力版本 |
| `abilityStatus` | `String` | `DEV`/`PRE`/`AUDIT`/`GRAY`/`ONLINE` |
| `abilityEnName` | `String` | 能力英文名称 |
| `abilityCnName` | `String` | 能力中文名称 |
| `templateCode` | `String` | 来源模板编码 |
| `templateVersion` | `String` | 来源模板版本 |
| `auditStatus` | `String` | `AUDITING`/`PASSED`/`REJECTED`/`CANCELED` |
| `abaoStatus` | `String` | 阿宝投放态：`PENDING`/`AUDITING`/`REJECTED`/`SYNCED` |

---

# 模板接口 (skill-template-mcp)

## querySelectableTemplates

### 请求参数 `SelectableTemplateQueryRequest`
| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `ownerOid` | `String` | 否 | 归属方 OID |

### 响应 `SelectableTemplateMcpVO`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `templateCode` | `String` | 模板编码 |
| `templateName` | `String` | 模板名称 |
| `templateDesc` | `String` | 模板描述 |
| `templateVersion` | `String` | 模板版本 |
| `templateMainType` | `String` | 模板主类型 |
| `industryCode` | `String` | 行业编码 |
| `industryName` | `String` | 行业名称 |
| `sceneCode` | `String` | 场景编码 |
| `sceneName` | `String` | 场景名称 |
| `generatorSkill` | `String` | 生成器 Skill 标识 |
| `introUrl` | `String` | 介绍文档 URL |
| `previewFlow` | `List<PreviewFlowStep>` | 预览流程步骤列表 |

## queryTemplateDetail

### 请求参数 `TemplateQueryRequest`
| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `templateCode` | `String` | 是 | 模板编码 |
| `templateVersion` | `String` | 是 | 模板版本 |


### 响应 `TemplateDetailMcpVO`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `Long` | 模板主键 ID |
| `templateCode` | `String` | 模板编码 |
| `templateName` | `String` | 模板名称 |
| `templateDesc` | `String` | 模板描述 |
| `templateVersion` | `String` | 模板版本 |
| `ownerCode` | `String` | 归属方编码 |
| `ownerType` | `String` | 归属方类型 |
| `templateMainType` | `String` | `SKILL` 等 |
| `status` | `String` | `DRAFT`/`PUBLISHED` |
| `gmtOnline` | `Date` | 上线时间 |
| `industryCode` | `String` | 行业编码 |
| `industryName` | `String` | 行业名称 |
| `sceneCode` | `String` | 场景编码 |
| `sceneName` | `String` | 场景名称 |
| `generatorSkill` | `String` | 生成器 Skill 标识 |
| `introUrl` | `String` | 介绍文档 URL |
| `previewFlow` | `List<PreviewFlowStep>` | 预览流程步骤 |
| `globalParamList` | `List<ParamVO>` | 全局参数列表 |
| `mcpServerParamList` | `List<ParamVO>` | MCP Server 参数列表 |
| `mcpToolList` | `List<McpToolVO>` | MCP 工具列表 |

### `ParamVO` 结构（步骤7 交互补参的权威）
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `paramType` | `String` | `GLOBAL`/`MCP_SERVER` |
| `paramName` | `String` | 参数名称（占位符 key） |
| `paramLabel` | `String` | 参数标签（展示用） |
| `subTitle` | `String` | 子标题 |
| `paramPlaceholder` | `String` | 占位提示 |
| `paramValueType` | `String` | 参数值类型 |
| `maxLength` | `Integer` | 最大长度 |
| `validationType` | `String` | 校验类型 |
| `validationRule` | `String` | 校验规则 |
| `required` | `Integer` | `0`(否)/`1`(是) |
| `defaultValue` | `String` | 默认值 |
| `description` | `String` | 参数描述 |
| `purpose` | `String` | 参数用途（**优先于 description 作为主解释**） |
| `example` | `String` | 示例值（**步骤7 格式一致性校验基准**） |
| `sortOrder` | `Integer` | 排序序号 |

### `McpToolVO` 结构
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `mcpServerParamName` | `String` | 关联的 MCP Server 参数名 |
| `toolName` | `String` | 工具名称 |
| `toolLabel` | `String` | 工具展示名称 |
| `required` | `Integer` | `0`/`1` |
| `inputSchema` | `String` | 输入 Schema（JSON 字符串） |
| `outputSchema` | `String` | 输出 Schema（JSON 字符串） |
| `toolDesc` | `String` | 工具描述 |

## checkTemplateWhitelist

### 请求参数 `TemplateQueryRequest`
| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `templateCode` | `String` | 否 | 模板编码（预留字段） |
| `templateVersion` | `String` | 否 | 模板版本（预留字段） |

> 基于 MCP 身份上下文 OID 检查，`templateCode`/`templateVersion` 当前未做必填校验。

### 响应 `TemplateWhitelistCheckMcpVO`
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `whitelistPassed` | `boolean` | 是否在白名单内 |
| `reason` | `String` | 未通过原因 |
| `applyGuidance` | `String` | 申请引导文案 |

---

# 工作空间接口 (space-query-service)

## query-space-list

### 请求参数 `SpaceListMcpRequest`
| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `keyword` | `String` | 否 | 空间名称关键词 |
| `pageNum` | `Integer` | 否 | 默认 `1` |
| `pageSize` | `Integer` | 否 | 默认 `20` |

> **响应结构特殊**：`{success, errorContext, resultObj}`（非 `Result<T>`），以 `success === true` 判定成功。
> **所需 scope**：`space:read`（`skill:all,app:all` 不覆盖，`space:all` 非法）。

### `SpaceVO` 结构
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `spaceId` | `String` | 工作空间 ID（**选定后即 workSpaceId**） |
| `spaceName` | `String` | 工作空间名称 |
| `spaceDesc` | `String` | 空间描述 |
| `owner` | `String` | 所属用户 OID |
| `gmtCreate` | `String` | 创建时间 |

> **无 `isDefault` 字段**：步骤2 的"默认空间"概念为纯客户端 UX 增强，不由 API 数据驱动。

---

# 小程序接口 (miniapp-query-tool)
> **结果处理**：如果查询成功，但是没有返回小程序列表，则提示没有小程序或当前登录账号不是小程序成员。
## query-mini-app-list

### 请求参数 `MiniAppListMcpRequest`
| 字段 | 类型 | 必填 | 说明               |
| --- | --- | --- |------------------|
| `keyword` | `String` | 否 | 小程序名称关键词，不能传空字符串 |
| `pageNum` | `Integer` | 否 | 默认 `1`           |
| `pageSize` | `Integer` | 否 | 默认 `20`          |

> 同 `space-query-service`，响应结构为 `{success, errorContext, resultObj}`。

### `MiniAppVO` 结构
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `appId` | `String` | 小程序 AppID（**miniAppAppId 取此值**） |
| `appName` | `String` | 小程序名称 |
| `appType` | `String` | 如 `TINYAPP_NORMAL` |
| `applicationType` | `String` | 如 `TINYAPP` |
| `status` | `String` | 如 `NORMAL` |
| `logoUrl` | `String` | Logo URL（可作 brandLogo 候选） |
| `oid` | `String` | 所属 OID（可作 MCP 查询 ownerCode） |
| `pid` | `String` | 所属 PID |
| `gmtCreate` | `String` | 创建时间 |
| `gmtModified` | `String` | 修改时间 |

### 调用示例
```bash
alipay-cli mcp call miniapp-query-tool.query-mini-app-list -d '{"request":{"keyword":"我的","pageNum":1,"pageSize":20}}'
```
```bash
alipay-cli mcp call miniapp-query-tool.query-mini-app-list -d '{"request":{"pageNum":1,"pageSize":20}}'
```
```json
// === 成功响应 ===
{
  "success": true,
  "errorContext": null,
  "resultObj": {
    "pagination": {
      "pageNum": 1,
      "pageSize": 20,
      "total": 2
    },
    "rows": [
      {
        "appId": "2021000123456789",
        "appName": "我的测试小程序",
        "appType": "TINYAPP_NORMAL",
        "applicationType": "TINYAPP",
        "status": "NORMAL",
        "logoUrl": "https://oalipay-dynamic-dx.alipay.com/xxx/logo.png",
        "oid": "2088000123456789",
        "pid": "2088000987654321",
        "gmtCreate": "2026-07-15 10:30:00",
        "gmtModified": "2026-07-20 14:20:00"
      },
      {
        "appId": "2021000987654321",
        "appName": "我的另一个小程序",
        "appType": "TINYAPP_NORMAL",
        "applicationType": "TINYAPP",
        "status": "NORMAL",
        "logoUrl": "https://oalipay-dynamic-dx.alipay.com/xxx/logo2.png",
        "oid": "2088000123456789",
        "pid": "2088000987654321",
        "gmtCreate": "2026-06-01 09:00:00",
        "gmtModified": "2026-06-10 11:00:00"
      }
    ]
  }
}
```

---


# 合约查询接口 (ar-query)

## 路由规则
| 已有参数 | 路由到 | 说明 |
|---|---|---|
| 有 `salesProductCode` | `queryArInfosBySalesProd` | 单个包装为 `["xxx"]` |
| 有 `backProdCode` | `queryArInfosByBackProd` | 单个包装为 `["xxx"]` |
| 都没有 | 不调接口 | 引导用户提供产品码 |

> 单次最多查询 5 个产品码，超出取前 5 个。

## queryArInfosBySalesProd
| 参数 | 来源 | 说明 |
|---|---|---|
| `salesProductCodes` | Skill 侧传入 | 前台产品码列表（最多5个） |
| `tntInstId` | 网关自动注入 | 不感知 |
| 操作者信息 | 上下文自动注入 | 不感知 |

## queryArInfosByBackProd
| 参数 | 来源 | 说明 |
|---|---|---|
| `backProdCodes` | 调用方传入 | 后台产品码列表（最多5个） |
| `tntInstId` | 网关自动注入 | 不感知 |
| `merchantPid` | 上下文自动填充 | 不感知 |

## `ArInfo` 返回结构
| 字段 | 说明 |
|---|---|
| `arNo` | 合约号 |
| `arStatus` | 合约状态 |
| `arStatusDesc` | 合约状态描述（优先展示） |
| `gmtValid` | 生效时间 |
| `gmtInvalid` | 失效时间 |
| `salesProductCode` | 前台产品码 |
| `salesProductName` | 前台产品名称 |
| `backProdCode` | 后台产品码 |
| `backProdName` | 后台产品名称 |
| `protocolInfo` | 协议信息（`name`+`protocolUrl`） |
| `priceDesc` | 价格描述 |

> **结果判定**：`data.arInfoList` 非空 → 已签约；为空 → 未签约。
> **`priceDesc` 铁律**：必须原文完整展示，禁止截断/摘要/只取数字/改写。
> `priceDesc`/`protocolInfo` 为空时追加提示"完整详情请前往商家中心查看"。

---

# 文件上传与同步辅助

## 文件上传（alipay-cli file upload）

```bash
alipay-cli file upload "<zip绝对路径>" -s aiskill --json 2>/dev/null
```

| 参数 | 取值 | 说明 |
|------|------|------|
| `<zip路径>` | 打包产出的 zip 绝对路径 | |
| `-s` | `aiskill` | Skill 产物 zip 上传专用，支持 `.zip` |
| `--json` | 必带 | 纯 JSON 输出 |
| `2>/dev/null` | 必带 | 丢弃 stderr |

> 禁止用 MCP 调用格式（`alipay-cli mcp call file.upload`）、省略 `-s`、加额外参数。

### 返回格式与 fileKey 解析
```json
// 成功
{ "success": true, "data": { "fileKey": "XDPMQ6yeOggAAAAAQ_AAAAgAeljUAQFr" } }
// 失败
{ "success": false, "error": { "code": "UPLOAD_FAILED", "message": "上传失败原因" } }
```

fileKey 兼容多种返回结构：
```bash
FILE_KEY=$(echo "$UPLOAD_RESULT" | jq -r '.data.fileKey // .data.data.fileKey // .fileKey // .result.fileKey // empty')
```

## configParamList 组装规则
- 由 `to_config_param.py` 自动组装，**仅 GLOBAL + MCP_SERVER**，排除 MCP_TOOL
- MCP_TOOL 工具绑定走 `mcpRelList`（`mcpAbilityCode` + `serverDiscoveryCode`）
- `configParamList` + `mcpRelList` 是 create/update 必填字段，**不能因报错就降级不传**
- 传入 MCP_TOOL 会报 `param[xxx] is not defined in template`

## 同步成功后最终产物结构
```json
{
  "status": "success",
  "message": "同步 AI 能力中心成功",
  "skill_output_path": "产物路径",
  "sync": {
    "zip_path": "zip 路径",
    "upload_file_id": "fileKey",
    "ability_code": "data.abilityCode",
    "ability_version": "data.abilityVersion"
  }
}
```
