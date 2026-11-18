# 卡片设计师 — Qoder Plugin

版本 **1.1.0**。本包仅完成本地制作与审阅准备，尚未上架；Qoder 宿主调用、服务端渠道可用性与实际审核结果仍需独立验证。

![公众号二维码关注图头像](./avatars/expert.png)

## 展示资料

- Plugin 展示名称：卡片设计师
- 原服务名称：公众号二维码关注图
- 中文职业头衔：卡片设计师
- English name: WeChat Follow Card Design
- English profession: WeChat Follow Card Design
- 中文简介：围绕真实账号名称、内容介绍和已有二维码设计关注图，支持文末横卡与分享方图，成图发布前需扫码核验。
- English description: Design WeChat follow cards around a real account name, content introduction and an existing QR image, with landscape or square layouts that require final scan verification.

### 标签

- 文末关注图 / Article-End Cards
- 账号介绍 / Account Introductions
- 二维码排版 / QR Image Layouts

### 快捷问题

1. 帮我做张公众号文末关注图，账号名称、简介和现成二维码发给你。

   Design an article-end follow card using my account name, introduction and existing QR image.

2. 做一张方便分享的方形账号介绍图，使用我提供的真实二维码。

   Create a square account-introduction image for sharing, using the real QR image I provide.

3. 先做一张公众号文末介绍底图，二维码位置留空，我之后自己放原码。

   Create an article-end introduction background with a blank QR area; I will place the original code later.

以上快捷问题与双语展示资料供人工审阅和上架表单使用；示例不代表本次用户授权，也不保证平台自动展示这些字段。

## 岗位协作

[需求整理](./skills/shenhuo-wechat-follow-card-brief/SKILL.md) → [设计执行](./skills/shenhuo-wechat-follow-card/SKILL.md) → [结果交付](./skills/shenhuo-wechat-follow-card-delivery/SKILL.md)。三个 Skill 共用同一任务与客户端，独立触发时也读取必要流程，不依赖宿主自动注入角色文档。

外部服务、运行环境与权限见 [CONNECTORS.md](./CONNECTORS.md)。本包没有声明市场 MCP Connector。

## 服务与调用

- 插件清单：[.qoder-plugin/plugin.json](./.qoder-plugin/plugin.json)；角色入口：[qoder.md](./qoder.md)。
- 本套件内嵌 [调用 Skill](./skills/shenhuo-wechat-follow-card/SKILL.md)、[能力说明](./skills/shenhuo-wechat-follow-card/references/designer-profile.md)和[完整执行流程](./skills/shenhuo-wechat-follow-card/references/workflow.md)。先读取这些文件，再按真实需求执行，不假定 Skill 已预加载。
- 固定调用 `des_2e4c84ea35e6` / `wechat_official_qr_code_designer`（公众号二维码）；保留既有发布能力与默认规格，不路由或覆盖设计师身份。
- 依赖 **Python 3.10+**。发行 ZIP 内的 Python 客户端使用标准库，可独立运行，无需克隆开发仓库；源目录的轻量入口在打包时替换为完整客户端。
- 离线自检按 Skill 中的可执行检查运行，不读取凭证、不联网、不创建任务；业务调用需要网络和有效授权，只有真实回执能证明任务完成。
- 已有个人 Key 时沿用。缺 Key 时说明可选渠道体验或网站注册，取得向神火发送需求及授权素材的同意后再领取体验；不要暴露 Key，不上传未授权素材。
- 渠道 code 为 `qoder`，实际资格与积分以服务端为准。明确张数原样传递，未指定时用 auto，不额外设置试用图片数量上限。
- 神火服务完成需求理解、必要追问、创意与生成；客户端持续跟踪同一请求并下载真实结果，超时不重复建项。
- 先交付成功下载的图片，再说明未完成项与恢复方式，不要求注册才能取回已成功图片。
- 试用作品实际交付后，按 [设计执行 Skill](./skills/shenhuo-wechat-follow-card/SKILL.md) 原样展示 1000 积分活动文案，再展示指定注册链接；体验项目不自动迁移。个人 Key 用户打开原账号真实项目。

## 头像与包边界

头像逐字节复用已确认的对应专家头像，位置为 [avatars/expert.png](./avatars/expert.png)。头像为 512×512 PNG、≤500KB；红色衣服胸前保留白色神火火焰及白色斜体 shenhuoai.com，不新增角标。本地头像用于审阅和上架素材，不将非规范头像字段加入插件清单。

本包只提供图片设计服务入口，不包含内部 Designer Skill 正文、生产凭证或自定义 MCP。功能范围、必需素材、明确排除项和本 Skill 不提供的修改能力，以能力说明和流程为准。

公开作者：chenyth / chenyth@gmail.com。平台依据：[Qoder 扩展上架指南](https://docs.qoder.cn/qoderwork/user-guide/qoderwork-extension-release-guide-skill-plugin-connector)。本地检查不能替代宿主实机验证或市场审核；暂不上架。
