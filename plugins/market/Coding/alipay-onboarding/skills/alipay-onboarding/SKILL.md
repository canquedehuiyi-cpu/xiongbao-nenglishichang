---
name: alipay-onboarding
description: 支付宝开放平台对接与集成的统一入口 Skill。任何涉及支付宝或开放平台的对接、集成、联调、接入、供给、上架、签名、网关、证书、密钥、沙箱/生产环境、app_id、账号、权限、签约、调试、提审、评测、通场、商业化、版本管理等场景,均加载本 Skill。<br/>当前已沉淀四条细分路由:①「供给上翻(阿宝 Skill 生产)」——面向支付宝阿宝的 Skill 自动化生产工具:交互式选择行业模板(景区购票/茶饮取餐/快餐点单,架构可扩展更多行业),收集品牌专属配置参数后自动生成品牌定制化 Skill,并一键同步至 AI 能力中心(createSkillAbility / updateSkillAbility)完成 Skill 的创建、更新与发布,实现从配置到投放的完整闭环;<br/>②「接入支付产品」——接入支付宝支付能力收钱下单(当面付/订单码/电脑网站/手机网站/APP/JSAPI 支付,预授权、商家扣款等;含下单、查单、退款、撤销、对账、回调、沙箱与多语言代码示例);<br/>③「签约开通」——签约支付宝支付产品(智能收/电脑网站/APP/JSAPI 支付)的流程编排:产品推荐、MCC 经营类目推荐(内置 mcc-recommender 子 Skill)、资质信息收集、签约申请提交、合约/订单状态查询。<br/>④「小程序发布与管理」——创建小程序、接口加签、基础信息/隐私/类目/域名配置、上传构建、体验版、提审、灰度与正式上架、版本管理、备案、成员管理、插件与能力订购,由 miniapp-publish 子 Skill 承载。未映射到的开放平台场景走公共章节(CLI/签名/错误码)后按需 Read 对应 reference 或追问用户。<br/>特别提示:当用户提到「阿宝」时,优先确认本 Skill 已加载且可被 Agent 调用,并按路由 ① 驱动阿宝 Skill 生产;若本 Skill 未加载,应提示用户安装后再继续。<br/>当用户提到支付宝、开放平台、对接、集成、接入、联调、签名、网关、证书、密钥、沙箱、生产、app_id、ISV、服务商、代调、app_auth_token、MCP、Skill、上架、AI 能力中心、供给上翻、能力上翻、阿宝、模版模式、行业模板、景区购票、茶饮取餐、快餐点单、品牌定制、createSkillAbility、updateSkillAbility、支付、收钱、下单、退款、查单、回调、对账、当面付、JSAPI、订单码、预授权、商家扣款、代扣、周期扣款、自动续费、小程序、账号入驻、权限、签约、开通产品、经营类目、MCC、类目推荐、合约查询、签约订单、智能收、调试、提审、评测、通场、商业化、版本号、小程序发布、小程序提审、小程序上架、体验版、灰度发布、备案、miniapprelease、alipay-cli miniapp、alipay-cli 等关键词时使用。
version: 0.0.7
---

# Alipay Onboarding

支付宝开放平台对接与集成的统一入口 Skill。本文件是分发器(prompt),根据用户意图路由到具体业务场景。

## 版本自检

满足以下任一条件时,Read `references/skill-update.md` 按其流程执行版本自检与更新提示;否则跳过直接进入业务路由:

- 用户明确提到"更新"、"升级"、"检查版本"
- 当前对话涉及提审、上架、通场、签约等关键流程

版本自检遵循 24 小时节流(`.last-check`)、semver 比较、网络失败静默跳过等约束,详见 reference。

## 业务路由

判断用户意图后,按以下路由加载对应 reference;无法判断时先追问用户,不要臆测。

### 公共基础(任何路由都先具备)

AlipayCLI 是贯穿所有场景的命令行工具(认证、MCP 工具调用、文件上传、诊断)。需要 CLI 用法时 Read `references/alipay-cli.md`。

### 路由 ①:供给上翻(阿宝 Skill 生产)

意图:面向支付宝阿宝,生产并上架 AI 可调用的 Skill。当前承载于 `skill-solution-scenic-generator` 子 Skill:交互式选择行业模板(景区购票/茶饮取餐/快餐点单,架构可扩展更多行业),收集品牌专属配置参数后自动生成品牌定制化 Skill,并一键同步至 AI 能力中心(createSkillAbility / updateSkillAbility)完成 Skill 的创建、更新与发布,实现从配置到投放的完整闭环。

> 用户提到「阿宝」时,先确认本 Skill 已加载且可被 Agent 调用,再 Read 子 Skill 进入阿宝 Skill 生产流程;若未加载,提示用户安装本 Skill。

→ Read `references/skill-solution-scenic-generator/SKILL.md`

### 路由 ②:接入支付产品

意图:接入支付宝支付能力收钱下单。覆盖当面付 / 订单码 / 电脑网站 / 手机网站 / APP / JSAPI 支付,以及预授权支付、商家扣款(代扣/周期扣款)等场景的下单、查单、退款、撤销、对账、回调;含全流程产品选型、沙箱环境创建与多语言代码示例。

→ Read `references/alipay-payment-integration/SKILL.md`

### 路由 ③:签约开通

意图:签约/开通支付宝支付产品(智能收、电脑网站支付、APP 支付、JSAPI 支付),或查询合约状态、签约订单进度。由签约编排子 Skill `ar-sign-skill` 承载:产品推荐 → MCC 经营类目推荐(其内部调用同级 `mcc-recommender` 子 Skill) → 资质信息收集 → 确认汇总 → 申请提交 → 合约/订单查询。仅面向个人开发者,不含解约链路(解约引导去支付宝商家中心)。

> 签约链路与路由 ②(接入支付产品收钱下单)的边界:用户要**开通/签约产品、查签约进度**走本路由;用户已完成签约、要**写代码接入支付**走路由 ②。

→ Read `references/ar-sign-skill/SKILL.md`

### 路由 ④:小程序发布与管理

意图:创建或管理支付宝小程序,完成接口加签、基础信息/类目/隐私/域名配置、源码或模板上传构建、体验版、提审、灰度/正式上架,以及版本查询/下架/回滚/删除、备案、成员管理、插件与能力订购。由 `miniapp-publish` 子 Skill 承载,支持从已有 appId 与当前状态继续,也支持用户指定的单步操作。

> 路由边界:小程序生命周期与发布走本路由;在小程序中写代码接入支付走路由 ②;开通/签约支付产品走路由 ③;面向阿宝生产并上架 AI Skill 走路由 ①。仅提到“小程序”或“上架”而目标不明确时,先明确用户要操作的对象。

→ Read `references/miniapp-publish/SKILL.md`

子 Skill 内按具体操作读取 `commands.md` 及附录,当前 CLI 命令与入参以本机 `--help` 为准,登录与授权检查按子 Skill 执行。小程序授权使用 `miniapp:all`;发布/删除等操作的影响说明与确认、扫码核身等人工节点按子 Skill 执行。

### 未映射场景

先走公共章节(CLI/签名/错误码),按需 Read 对应 reference,或追问用户明确意图。

## 目录结构

```
alipay-onboarding/
├── SKILL.md                       # 本文件,分发器 + 版本自检
├── CHANGELOG.md                   # 版本 changelog(CI 提取写入 manifest)
├── references/
│   ├── alipay-cli.md              # AlipayCLI 使用说明(公共基础)
│   ├── skill-update.md            # 版本自检与更新流程
│   ├── alipay-payment-integration/    # 接入支付产品 子 Skill(产品选型/沙箱/多语言代码示例)
│   │   ├── SKILL.md
│   │   └── references/            # alipay-sandbox / code-examples(java/python/php/nodejs/csharp) / main
│   ├── skill-solution-scenic-generator/  # 供给上翻/阿宝 Skill 生产 子 Skill(模板化 Skill 生产与上架)
│   │   ├── SKILL.md
│   │   ├── scenic-references/    # MCP 方法 / CLI 命令 / 上架同步 等权威参考
│   │   ├── scenic-scripts/       # 校验/生成/修正/写入/打包/组装参数 脚本
│   │   └── scenic-templates/     # 行业模板(景区购票/茶饮/快餐)
│   ├── ar-sign-skill/            # 签约开通 子 Skill(签约编排:推荐/收集/提交/合约与订单查询)
│   │   ├── SKILL.md
│   │   ├── ar-sign               # 签约 Skill 统一入口命令(数据目录配置/清理)
│   │   ├── references/            # recommend-product / preview / apply / query-ar / query-order / mcp-guide / schema-guide / page-fallback
│   │   ├── scripts/              # 请求构建与配置辅助脚本
│   │   └── version.json
│   ├── miniapp-publish/          # 小程序发布与管理 子 Skill
│   │   ├── SKILL.md              # 生命周期流程与业务约束
│   │   ├── commands.md           # 各业务动作的命令与输入输出说明
│   │   └── appendix/             # security-and-identity / dangerous-op-confirm / o-station-routing / param-schemas
│   └── mcc-recommender/          # MCC 经营类目推荐 子 Skill(被 ar-sign-skill 调用,也可独立使用)
│       ├── SKILL.md
│       └── references/            # mcc_reference.md(个体超开可用类目)
└── scripts/                       # Skill 依赖的可执行脚本
```

> `manifest.json` 由发布流程生成,随 skill 一并发布:每个版本一份不可变产物(zip / manifest / setup),最新版本通过 `https://opengw.alipay.com/alipaycli/skill/alipay-onboarding/manifest` 获取,setup 引导见 `https://opengw.alipay.com/alipaycli/skill/alipay-onboarding/setup`。仓库 `skills/` 同级存放 `alipay-onboarding-setup.md`(一键安装引导源文件)。
