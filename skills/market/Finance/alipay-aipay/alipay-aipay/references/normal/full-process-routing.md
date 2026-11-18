# 完整接入编排

本文件是 `full_process` 唯一入口。启动方案送达前只复用 Integration 步骤 1 的项目、语言、当前系统分支环境和沙箱准备；不得开发代码、进入 Onboarding 或读取开通信息。

目标项目和技术栈确定后执行 `node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" flow integration entry`，只加载当前入口阶段并按步骤 1/2 准备及展示方案；代码开发满足衔接条件后执行 `node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" flow onboarding entry`。禁止整读两个 flow。所有 Skill 自有运行时动作只用当前 Skill 绝对路径下的统一入口单命令执行，不前置 `cd`、不拼接管道；用户项目命令仍以已确认项目根为 workdir。

其他 Skill 相对命令以 `references/normal/` 为 workdir。保留原始 `PROJECT_INPUT`；明确新建产物用 `--intent new`，名称/位置由 Agent 解析为 `TARGET_PROJECT_PATH`，runner 只校验；登记默认表达才省略。复用须选定项目根，未知位置先定位候选；“当前目录”仅在 runner 识别为项目根时接受。后续只用解析后的绝对路径。

## 边界

- 只编排 Integration 与 Onboarding，不复制其状态、完成条件和红线。完整接入复用 Integration 步骤 2 的唯一非阻塞 `integration.start.confirm`、同一检查器事实和模板，本轮只渲染一次。
- 先确定项目、服务端语言和创建方式；框架按 Integration 登记的 `framework-resolve` 解析，不把框架未知当作补问条件。`NEW_PROJECT` 空路径检查后使用该 runner 默认或用户明确框架初始化最小骨架，再执行 Integration 步骤 1；沙箱不依赖产品、不传 `PRODUCT`、不展示摘要，待配置仍继续。代码开发方案送达前禁止读取/展示 MCC、授权范围和开通材料/待办。
- 项目事实只来自 runner 与实际文件。未知位置用 `locate-projects --search-input "$SEARCH_INPUT" --format message` 查标记并等待选择；不得扫描上层大目录。完整性仍以 Integration 全部适用项和 checklist 为准。

## 新项目准备与路由分类

项目来源互斥：`CURRENT_PROJECT` 为当前目录内项目根，`OTHER_PROJECT` 为用户以绝对路径提供的目录外项目；未选定/不可访问/不可识别则为 `PROJECT_UNRESOLVED`，禁止凭描述生成状态。

`NEW_PROJECT` 只用于初始化前。含名称或位置时执行：

```bash
node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" integration-message resolve-project --project-input "$PROJECT_INPUT" --target-path "$TARGET_PROJECT_PATH" --base-path "$USER_WORKSPACE_ROOT" --intent new
```

登记默认表达时执行：

```bash
node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" integration-message resolve-project --project-input "$PROJECT_INPUT" --base-path "$USER_WORKSPACE_ROOT" --intent new
```

第二条只接受“新建项目”或“帮我新建默认项目”，使用用户目录下 `alipay-aipay-projects/pay-demo`，非空占用则加安全后缀；其他自然语言缺 `--target-path` 时保持未解析，禁止原话目录或默认回退。仅 `preparationStatus=READY` 才继续；框架由 Integration 的 `framework-resolve` 按语言默认或用户明确值初始化，其他结果不得清空/覆盖。初始化且沙箱终态确定后单向成为本轮 `PREPARED_NEW_PROJECT`；不持久化，重入重扫。`NEW_PROJECT` 不扫描代码。

### 固定检查器与 runner 终态协议

- `resolve-project --intent new` 只接受退出码 0、唯一 JSON、绝对 `projectPath`、`projectSelection/projectOrigin=NEW_PROJECT`、`projectOriginLabel=本轮新建项目` 和 `preparationStatus=READY`；否则保持 `PROJECT_UNRESOLVED`。
- `resolve-project --intent existing` 只接受退出码 0、唯一 JSON、规范化绝对路径、`CURRENT_PROJECT|OTHER_PROJECT` 和 `EXISTING_PROJECT/现有项目`。相对路径限 `--base-path` 内，目录外由用户提供绝对路径；失败不得以描述/cwd 代替。
- `locate-projects` 用于未知位置/多候选，缺省搜索词为 `当前目录`。stdout 是唯一候选消息；选择后仍执行 `resolve-project --intent existing`。
- `start-confirm` 内部只执行一次项目扫描，校验后将同一对象交给 renderer；失败为 `STATUS_UNKNOWN`。禁止改写命令、另跑扫描、抽取代码，或追加 `find`、`ls`、`stat`、额外 `jq` 和临时脚本复核同一结果。

## 维度二：目标产品集成状态

项目和沙箱取得确定终态后再确定产品并扫描合法项目分类。已有描述能唯一映射时直接复用；否则只执行下列消息并等待，仍不唯一时重复同一消息。目标产品明确前不得执行 `scan`。

```bash
node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" integration-message product-clarify
```

- `TARGET_PARTIAL`：发现目标代码/配置，仍完整验证；并存时优先。
- `OTHER_PRODUCT_ONLY`：仅有其他产品，保留。
- `NO_PAYMENT`：无支付能力。
- `STATUS_UNKNOWN`：不可访问、证据冲突/不足或产品不明，停止。

合法项目分类与前三种代码状态确认后进入 Integration；`PROJECT_UNRESOLVED/STATUS_UNKNOWN` 继续澄清。Unix/macOS/Linux 的 `CREATE_PENDING|VERIFY_PENDING` 和 Windows 的 `VERIFY_PENDING` 都不阻止扫描/开发。新项目保留 `projectOriginLabel=本轮新建项目`；已有项目“新建”只能新增能力或使用空路径。这些分类只用于本轮分流，不持久化。

## 完整接入启动方案

合法项目分类、前三种代码状态、产品、服务端语言和 runner 解析的框架全部确定后才能输出非阻塞 `integration.start.confirm`。缺项目或服务端语言时执行下列 `integration.context.required`；只缺新项目位置用 `integration.project_path.required`，只缺框架不补问。禁止使用 AskUserQuestion、request_user_input、宿主超时默认值、Agent 自创选项或自由话术替代；不得先输出扫描摘要或方案。

```bash
node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" integration-message context-required --missing-items "$MISSING_ITEMS"
```

`MISSING_ITEMS` 只由 `项目路径`、`技术栈` 组成，其中 `技术栈` 仅表示服务端语言缺失；产品不明确仍用 `product.clarify`。stdout 原文发出后等待，未补齐前不得初始化、安装或修改。路径输入均先 `resolve-project`；未知位置或需候选时执行：

```bash
node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" integration-message locate-projects --base-path "$USER_WORKSPACE_ROOT" --search-input "$SEARCH_INPUT" --format message
```

字段齐备后执行唯一 runner；禁止拆开执行项目扫描、`jq` 或 renderer，也不得附加解析。runner stdout 是本动作唯一对客消息；只有取得唯一 `CUSTOMER_MESSAGE_DELIVERY_REQUIRED=integration.start.confirm` 才能继续。命令后的下一个动作必须把 stdout 作为可见进行中消息原文送达，不得作为最终答复结束当前回合，送达前禁止调用工具；送达后同一回合立即进入 development loader，不得总结、询问、等待回复或再次校验项目快照。用户中断后若方案事实变化，重新澄清、扫描并输出当前方案；静态扫描只决定进入验证，不证明完成。

```bash
node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" integration-message start-confirm --product-type "$PRODUCT_TYPE" --product-name "$PRODUCT_NAME" --project-path "$PROJECT_PATH" --project-selection "$PROJECT_SELECTION" --language "$SERVER_LANGUAGE" --framework "$FRAMEWORK" --framework-source "$FRAMEWORK_SOURCE"
```

上面命令失败时不得展示手写确认或进入子流程。成功时必须取得唯一 `ALIPAY_AIPAY_INTERNAL:CUSTOMER_MESSAGE_DELIVERY_REQUIRED=integration.start.confirm`；缺失或重复视为失败。参数必须是当前确定值，禁止直接拼用户输入。runner 校验产品 variant 并固定服务声明；实际范围仍取当前 Integration flow 和 checklist。

分流、展示和交接事实必须来自 runner 内同一次 `scan` 对象；禁止用描述、Agent 自报或历史分类代替。`evidence` 仅内部校验，不进 renderer；Onboarding Step 1 前禁止传/猜 `mccCode`。只有方案 stdout 已按交付 marker 可见送达，才同时满足 `INT.START.PLAN_DELIVERED` 与 `INT.SERVICE_STATEMENT.DELIVERED`，随后直接执行 `node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" flow integration development --product-type "$PRODUCT_TYPE"`。loader 在原位置记录兼容 stage 和预开发阅读 stage，禁止手工执行 telemetry；不得解码内部值、重复扫描或再次渲染 `integration.start.confirm`。

合法组合必须确定产品、路径/来源、代码状态、语言/框架、服务声明和顺序；发现其他产品时保留。零散信息、`新建` 选择、未选候选或新项目未准备均不能替代完整机器校验。方案送达后仍完整执行 Integration 和 checklist。

## 子流程衔接规则

- 启动方案送达后直接进入 Integration 步骤 3；用户中断后若项目、产品、语言或框架变化，重新澄清和扫描并输出当前方案。
- Integration 先完整执行和校验。只有沙箱待配置，或 READY 且仅剩非阻塞人工待验证项时，保持“部分通过”进入 Onboarding；其他代码、安全或依据缺口停在 Integration，不提前登录或收集开通材料。
- 阶段间只复用有效的产品、项目、代码产物和 CLI 检查，不再询问是否进入 Onboarding；Onboarding 只保留非阻塞方案展示。
- 授权后分别查询签约、应用和适用服务；分支独立，单分支失败不回滚其他成功，认证/授权不匹配或主体变化全局阻断。一次只收集一个类别，提前材料直接校验且不重复索取。
- 签约材料通过后直接提交；服务创建摘要后直创、修改仍确认；空应用候选材料完整或非空候选明确新建，重查未变即创建，以用户公钥生成官方确认页，校验成功后直接提审。均不增加额外确认点；按量付费沙箱测试仍属 Integration 默认动作。
- 当前终点汇总代码、沙箱、签约、服务、应用和待办；人工待验证项带入 Onboarding Step 6，不增加确认。有待生效/审核/验证或配置缺口时不得宣称生产就绪。
