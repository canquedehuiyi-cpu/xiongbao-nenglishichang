# 支付宝 AI 付 Skill
## 支持范围

仅支持 AI 按量付费、AI 网页应用收款、AI 移动应用收款；“按量付费”“网站支付”“APP 支付”等旧称仅作输入别名，对客仍用新名称。明确要求当面付、付款码、订单码支付、JSAPI 支付、预授权支付或商家扣款时不得改判，按 `normal/rejection-guide.md` 受控拒绝。

AI 网页应用收款覆盖 PC 网页和手机浏览器/H5，接口固定 `alipay.trade.page.pay`，签约固定 `productType=webpay`、`salesCode=I1080300001000041203`、`appType=PC_WEB`；`PC_WEB` 不表示仅 PC。

## 执行红线

1. **流程与确认**：按 flow 顺序执行；阻塞确认只认用户对当前摘要的明确回复，不以工具超时、默认值或 Task 状态代替，不增未登记操作、材料或确认。
2. **事实与依据**：禁止编造配置、状态、结果或规则；无当前实现、实际返回或官方依据时说明无法确认。额度解限、可收款时间和产品开通问题用[支付宝商家平台](https://b.alipay.com/page/portal/home)，代码、应用创建和发布问题用[支付宝开放平台](https://open.alipay.com/)或[支付宝技术支持](https://opensupport.alipay.com/support/intelligent-services?form=payskill)。静态扫描或提交成功不等于完成。
3. **CLI/MCP 契约**：优先用动作处脚本；直调的完整方法和 JSON 仅来自已读文档或 `alipay-cli mcp list <server> --json` 实时 schema。遇到 `Server not found`、`Method not found`、`Invalid params` 立即停下核对，禁止试近似名称。
4. **联网权限**：`alipay-cli` 登录/MCP、上传、沙箱创建和下载按联网命令处理；支持显式授权时首次即申请，详见 `normal/alipay-cli-env.md`。
5. **用户文件**：只改已确认项目和范围，不清空或删除既有项目；“新建/重做/换一个”不是删除授权。具体删除仍遵守 Integration flow 的清单、二次确认和禁删边界。
6. **敏感信息**：应用公钥仅由用户生成并明确提供；禁止请求/处理生产私钥、生成密钥对、补全/改写公钥或添加 PEM 头尾。敏感值、临时 URL 和沙箱资料遵守对应 flow/script 的白名单、权限和输出边界。
7. **沙箱结论**：真实快速沙箱配置不得用占位值，唯一例外是 AI 按量付费沙箱 `service_id=api_mock_service_id`，且生产禁用。`CREATE_PENDING|VERIFY_PENDING` 只允许继续代码实现，阻止字段使用、摘要、后置校验、联调和付款体验。字段校验不等于支付测试；仅完整 402 链路满足 flow 才可称沙箱测试通过。
8. **异步通知**：AI 网页应用收款/AI 移动应用收款必须实现通知。本地无公网 HTTPS `notify_url` 时可不传并以交易查询验收，公网通知联调列为人工待验证；生产上线前须恢复通知并完成验签、幂等、关键字段校验、`success` 回写和补偿查询，否则不宣称生产就绪。
9. **受控页面**：授权链接仅由 `auth.sh` 按固定产品/MCC 生成，只允许 `https://aipay.alipay.com/cli-auth` 及登记参数，禁用 CLI `verification_url`；公钥页和系统 opener 只走登记脚本。失败后宿主内置浏览器只可打开已交付的同一 URL 一次；仍失败才提示手动打开，再有限轮询。禁止搜索、改写或自动操作；opener/config 写失败不算业务失败。
10. **对客输出**：指定 runner/renderer/脚本时，stdout 是唯一对客正文，须原文回复且不加旁白；工具输出记录、折叠面板或日志不等于已对客发送。展示命令只执行登记单条命令，禁 `2>&1`、管道、`grep/sed/awk/tee`、临时包装或拆回 `jq/printf/renderer`。除 `self_update.mjs` 的 `SELF_UPDATE:*` stderr 终态外，内部事实行均以 `ALIPAY_AIPAY_INTERNAL:` 开头；宿主合并输出时仍整行剔除，严禁对客。`integration.start.confirm` 和 `onboarding.plan.confirm` 成功时必须各自产生唯一 `ALIPAY_AIPAY_INTERNAL:CUSTOMER_MESSAGE_DELIVERY_REQUIRED=<messageId>`；下一动作先将 stdout 可见送达，不得以最终答复结束回合，送达前禁工具；送达后同回合继续，不等待回复。所有 `postRenderHintType=scanReturn` 的页面消息都是交付屏障（当前为 `auth.page`、`application.key.page`）：先独立送达页面 stdout，再执行受控 opener 和有限轮询，不合并 pending/收口；不要求确认。阻塞正文后等待；剔除内部行后正文为空则直接转移。
11. **确定性转移**：固定脚本终态后立即转移；只执行动作处登记命令，禁止追加 `jq/cat/grep/curl` 或临时脚本重复解析。失败只走登记恢复；项目自检不绕过 Skill 脚本或打印敏感配置。

## 标准消息

`normal/json/customer-messages.json` 是稳定对客正文唯一目录。Integration 启动使用 `node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" integration-message start-confirm`，收口使用 `node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" integration-message checklist-result`；Onboarding 的 MCC、发现、材料、候选、收口及授权、公钥页、密钥工具、错误均用登记 runtime 动作。`process.partial_result` 必须发送 closeout 动作的完整 stdout，缺少 AI 网页应用收款上线关键点或收款限制引导即未送达。仅无托管入口时直调 renderer：

```bash
node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" render --schema <messageId> --variant <VARIANT>
node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" render <messageId> --variant <VARIANT> --input-json "$MESSAGE_INPUT_JSON"
```

动态 JSON 只取本轮事实；无变量传 `{}`，禁止字符串替换或 `eval`。正常路径禁止预跑 `render --schema` 或用 `jq`/消息目录探测字段。renderer 返回 `MESSAGE_RENDER_ERROR` 时必须先复查同一 `messageId` + `variant` schema，禁止猜枚举；非 0 即停止，不手写兜底。

阻塞点展示登记摘要后，把用户原始回复交给 `node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" reply confirm --reply "$USER_REPLY" --input-id "$USER_INPUT_ID"`；仅唯一 `ALIPAY_AIPAY_INTERNAL:REPLY_DECISION=CONFIRMED` 可推进。`1`、`继续/继续推进`、`好了/已完成`、`确认/确定/同意`、`OK` 等明确肯定表达等价；否定、疑问、取消、修改或含糊回复不确认。确认只绑定当前产品、项目、主体、候选和摘要，任一变化即失效；此校验不新增操作点。

`<SKILL_DIR>` 是启动器确定的当前 Skill 规范化绝对路径占位符，不是 shell 变量。Skill 自有受控 Node、Shell 和 Python 入口必须使用文档登记的 `<SKILL_DIR>/references/...` 绝对路径单命令执行，禁止前置 `cd`、拼 `&&`、管道或退回相对路径；这些入口不新增权限确认或业务操作点。未登记命令和用户项目命令仍使用所在 Markdown 目录或已确认项目根，不得借用 Skill 权限。

## 入口路由

根 `SKILL.md` 启动器已经在读取本文件前确定本轮有效版本。运行时禁止再次执行自更新、读取 `normal/self-update.md` 或切换其他副本；只按原始请求识别根意图并加载入口：

| 意图 | 判定 | 入口 | 后续按需加载 |
|---|---|---|---|
| `integration_only` | 只要求代码开发、支付集成或集成排障，未同时要求产品开通 | 执行 `node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" integration-bootstrap --root-intent integration_only --input-id "$USER_INPUT_ID"` | 当前阶段、产品和语言的契约、示例与脚本 |
| `onboarding_only` | 只要求签约、入驻或产品开通，未同时要求代码开发 | 执行 `node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" onboarding-bootstrap --root-intent onboarding_only --input-id "$USER_INPUT_ID"` | 当前阶段的授权、查询或写分支模块 |
| `full_process` | 明确要求完整接入、一站式，或同一请求同时要求代码开发和产品开通 | `normal/full-process-routing.md` | 先 Integration，满足衔接条件后 Onboarding |

`integration_only` 的 `integration-bootstrap` 只在同一 Node 进程串行执行 `telemetry start-run` 与 `flow integration entry`。`onboarding_only` 的 `onboarding-bootstrap` 只串行执行 `telemetry start-run`、`onboarding-message platform-entry` 与 `flow onboarding entry`。两者均为既有无业务写入动作，执行后不得重复原子命令。Windows 引导渲染即终结 run 并停止，`platform_id` 取本次 `run_id` 且禁止 Agent 传入；非 Windows 返回 entry 契约。`full_process` 不使用 `integration-bootstrap`；衔接 Onboarding 也不使用带 `start-run` 的 bootstrap，仍执行 `node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" onboarding-message platform-entry` 后按需加载 entry，避免重复 `run.intent_detected`。

`full_process` 识别根意图后立即执行 `node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" telemetry start-run --root-intent full_process --input-id "$USER_INPUT_ID"`；产品已唯一确定时追加 `--product-type <aipay|webpay|apppay>`。`integration_only` 和 `onboarding_only` 已由上表各自 bootstrap 包含同一次 `start-run`，不得重复执行本条 telemetry。命令创建/复用当前流程 `run_id`，并在遥测开启时记录 `run.intent_detected`：同一意图和产品继续复用，`UNKNOWN` 补全产品仍复用同一 `run_id`；明确换产品、换根意图或既有 run 已终态才重建。第三方平台项目 ID 仍优先固定为 `run_id`，不得被显式 run ID 或本地生成值覆盖。业务 stage 只由登记 runner/script 异步记录。

遥测默认开启，`ALIPAY_AIPAY_TELEMETRY=0|false|off|no` 关闭事件/outbox/上传/flush；私有 run context 仍供 `PLATFORM_ID` 与终态生命周期。失败静默，不改变业务/消息/确认，stdout 空且 stderr 内部行不对客。`integration_only` 由 checklist 终结；Onboarding 由 closeout 或登记提前终止消息终结。上报权限不新增网络探针；实际低敏上传就是自然探测，collector 可达时不申请。任一终态后若 telemetry outbox 因 DNS、连接或超时失败积压，按 `normal/telemetry.md` 先本地状态判断，确实需要时按需申请补传权限；`flush-outbox` 前台小批量补传并优先发送 `run.terminal`，失败仍不影响业务收口。

用户输入计数是入口前置职责，统计窗口从首次触发本 Skill 的用户消息开始，到当前 `run_id` 的 `run.terminal` 事件生成为止。只计用户在 Agent 对话框发送的消息，不计宿主/系统/网页授权、扫码、Skill stage、runner、工具调用或自动轮询。文字、图片/文件、空白/短确认、材料补充、确认回复和中途插话都按一条用户消息计；同一条消息含文字和图片/文件仍只计一条。`USER_INPUT_ID` 是当前用户消息的本地幂等键：Agent 从首次触发本 Skill 起，给每条新用户消息分配对话内单调序号，同一消息重试复用同一值。`USER_INPUT_ID` 不得包含或派生自用户输入内容、文件名、路径、截图/OCR、业务材料、stage 名或工具调用序号；运行时只保存其本地 hash，不上报。

`start-run` 自动把触发当前 run 的首条用户输入计为 `before-flow`；中断/压缩后以新 `USER_INPUT_ID` 重入同一未终态 run 时，`start-run` 按当前 phase 幂等补计该消息。阻塞确认统一通过 `reply confirm --reply "$USER_REPLY" --input-id "$USER_INPUT_ID"`，该 runner 自动按当前 phase 幂等计数，禁止再为同一确认回复额外执行 `telemetry count-user-input`。其他用户输入（中途打断、补材料、只上传图片/文件、只问问题等）若不经 `reply confirm` 或 onboarding recovery，先于任何 Skill 动作或业务答复按当前 phase 执行一次 `node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" telemetry count-user-input --phase before-flow|after-flow --input-id "$USER_INPUT_ID"`；重复同一 `USER_INPUT_ID` 不加计。`*.user_confirmed` 由 flow loader 自动标记起点但不计数，after-flow 从其后的下一条用户消息开始，前置澄清和候选不计 after-flow，`full_process` 不因 Onboarding 重置。closeout 默认从本地 run state 派生计数；状态为空时用首条输入的最小合法计数，状态不可用且已核对时才显式传三项，runner 拒绝缺项、负数、`after > total`、已观测 flow start 但 `after >= total`。`terminal_reason` 为终态 runner 写入的固定低敏枚举，禁自由文本、错误详情和业务响应。不新增业务确认点或独立上报；入队后当前 `run.terminal` 文件做短超时前台 drain，失败保留 outbox 且不影响业务收口，网络类失败进入通用补传判断。脚本以当前 `run_id` 为 `PLATFORM_ID`；Agent 不手写环境前缀或改 MCP payload；维护诊断/outbox/上传/flush 见 `normal/telemetry.md`。

三种入口均只在无法从已有产品名称或业务描述可靠确定唯一产品时执行 flow 登记的 `product-clarify` runner；不得推定或手写澄清。产品明确但 MCC 尚无检索输入时使用 `mcc-clarify`；已有经营描述后先按 Onboarding flow 读取一次当前 `<SKILL_DIR>/references/onboarding/modules/mcc-reference.md` 做 Agent 语义候选，再统一调用 `mcc-resolve-plan` 由 runner 复核、合并和渲染；用户直接提供当前表内完整 MCC 编码时可跳过 Agent 泛化并由 runner 精确校验。不得拆回 `mcc-search + mcc-candidates`、先旧检索失败后临时猜测，或为方案展示再拼 renderer 输入。

代码开发或完整接入缺项目位置/服务端语言时，使用 `integration.context.required` 或 `integration.project_path.required` 标准消息；框架缺失不触发补问。先区分新建与复用并保留原始 `PROJECT_INPUT`。明确新建产物固定用 `resolve-project --intent new`；含名称或位置时由 Agent 解析 `TARGET_PROJECT_PATH` 并传 `--target-path`，runner 只校验路径和目录状态，不解析自然语言或把原话当目录名；纯默认新建才省略。现有项目未知时先定位候选；所有路径经 `resolve-project` 后再用 `framework-resolve`：新项目取语言默认框架，现有项目从依赖推导或沿用结构，用户明确框架优先。补齐前不初始化、装依赖或改文件。

每轮代码开发只渲染一次非阻塞 `integration.start.confirm`，覆盖步骤 1 至步骤8：代码开发校验；对应 `CUSTOMER_MESSAGE_DELIVERY_REQUIRED` marker 唯一且 stdout 可见送达后，直接进入步骤 3，不生成或复验方案 receipt。after-flow 起点：`full_process=integration.user_confirmed` 且 Onboarding 不重置，`onboarding_only=onboarding.user_confirmed`，前置澄清/方案不计。Onboarding 只保留一次非阻塞方案展示；同样只有 marker 唯一且 stdout 已可见送达，才允许在 MCC 唯一事实有效后执行 `node "<SKILL_DIR>/references/normal/scripts/runtime.mjs" onboarding-execute-ready --product-type "$PRODUCT_TYPE"`。该组合动作只串行加载 `flow onboarding execute` 并执行既有 `env check`，不跨用户输入、授权页或任何写操作；执行后不得再重复单独加载 execute phase 或重复环境检查。两类方案送达后都自动继续，不等待回复。服务修改仍保留绑定当前摘要的阻塞确认。签约材料完整后直接提交，服务创建摘要后直接创建，新建应用公钥校验成功后直接提审。

扫码页非阻塞：授权最多 12 次/间隔 5 秒，公钥最多 20 次/间隔 2 秒，成功即推进；耗尽后经统一回复判定只查一次，不重启轮询。

`full_process` 代码开发方案送达前只准备项目、语言、系统分支环境和沙箱；Windows 未明确要求当前配置时记 `VERIFY_PENDING`，不收资料。方案送达后直接进入 Integration 步骤 3，满足条件自动进 Onboarding；仅沙箱待配置，或 READY 且只剩非阻塞人工验证时可部分通过，其他缺口停在 Integration；收口保留全部待办。用户中断后重新确认当前项目和服务端语言，从实际项目扫描恢复，不恢复旧方案状态。

仅代码开发结束时提醒仍需产品开通；仅产品开通结束时提醒仍需代码开发。机器规则、消息目录、fixture 和测试不作为默认必读内容。
