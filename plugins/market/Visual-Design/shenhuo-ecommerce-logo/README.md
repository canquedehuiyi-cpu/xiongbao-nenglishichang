# 商标设计师 — Qoder Plugin

版本 **1.1.0**。本包仅完成本地制作与审阅准备，尚未上架；Qoder 宿主调用、服务端渠道可用性与实际审核结果仍需独立验证。

![电商 LOGO头像](./avatars/expert.png)

## 展示资料

- Plugin 展示名称：商标设计师
- 原服务名称：电商 LOGO
- 中文职业头衔：商标设计师
- English name: Ecommerce Logo Images
- English profession: Ecommerce Logo Images
- 中文简介：从准确店名与主营商品出发，设计清楚好认的店铺标志图片，支持原标改名、横向组合和单色版本。
- English description: Create recognizable online-store logo images from an exact name and product range, including renaming, horizontal layouts and monochrome versions.

### 标签

- 店铺标志 / Store Logos
- 原标修改 / Logo Edits
- 同标适配 / Logo Variations

### 快捷问题

1. 给我的网店做一个 LOGO，准确店名和主营商品我发给你。

   Create an online-store logo using the exact store name and main products I provide.

2. 把这个已有 LOGO 改成横向组合，图形、名称和品牌特征保留。

   Rearrange this existing logo into a horizontal layout while preserving the symbol, name and identity.

3. 只把这个 LOGO 的旧店名换成新店名，其他图形和颜色保留。

   Replace only the old store name in this logo with the new name, preserving the other shapes and colors.

以上快捷问题与双语展示资料供人工审阅和上架表单使用；示例不代表本次用户授权，也不保证平台自动展示这些字段。

## 岗位协作

[需求整理](./skills/shenhuo-ecommerce-logo-brief/SKILL.md) → [设计执行](./skills/shenhuo-ecommerce-logo/SKILL.md) → [结果交付](./skills/shenhuo-ecommerce-logo-delivery/SKILL.md)。三个 Skill 共用同一任务与客户端，独立触发时也读取必要流程，不依赖宿主自动注入角色文档。

外部服务、运行环境与权限见 [CONNECTORS.md](./CONNECTORS.md)。本包没有声明市场 MCP Connector。

## 服务与调用

- 插件清单：[.qoder-plugin/plugin.json](./.qoder-plugin/plugin.json)；角色入口：[qoder.md](./qoder.md)。
- 本套件内嵌 [调用 Skill](./skills/shenhuo-ecommerce-logo/SKILL.md)、[能力说明](./skills/shenhuo-ecommerce-logo/references/designer-profile.md)和[完整执行流程](./skills/shenhuo-ecommerce-logo/references/workflow.md)。先读取这些文件，再按真实需求执行，不假定 Skill 已预加载。
- 固定调用 `des_f06a89ff1e71` / `ecommerce_logo`（电商 LOGO）；保留既有发布能力与默认规格，不路由或覆盖设计师身份。
- 依赖 **Python 3.10+**。发行 ZIP 内的 Python 客户端使用标准库，可独立运行，无需克隆开发仓库；源目录的轻量入口在打包时替换为完整客户端。
- 离线自检按 Skill 中的可执行检查运行，不读取凭证、不联网、不创建任务；业务调用需要网络和有效授权，只有真实回执能证明任务完成。
- 已有个人 Key 时沿用。缺 Key 时说明可选渠道体验或网站注册，取得向神火发送需求及授权素材的同意后再领取体验；不要暴露 Key，不上传未授权素材。
- 渠道 code 为 `qoder`，实际资格与积分以服务端为准。明确张数原样传递，未指定时用 auto，不额外设置试用图片数量上限。
- 神火服务完成需求理解、必要追问、创意与生成；客户端持续跟踪同一请求并下载真实结果，超时不重复建项。
- 先交付成功下载的图片，再说明未完成项与恢复方式，不要求注册才能取回已成功图片。
- 试用作品实际交付后，按 [设计执行 Skill](./skills/shenhuo-ecommerce-logo/SKILL.md) 原样展示 1000 积分活动文案，再展示指定注册链接；体验项目不自动迁移。个人 Key 用户打开原账号真实项目。

## 头像与包边界

头像逐字节复用已确认的对应专家头像，位置为 [avatars/expert.png](./avatars/expert.png)。头像为 512×512 PNG、≤500KB；红色衣服胸前保留白色神火火焰及白色斜体 shenhuoai.com，不新增角标。本地头像用于审阅和上架素材，不将非规范头像字段加入插件清单。

本包只提供图片设计服务入口，不包含内部 Designer Skill 正文、生产凭证或自定义 MCP。功能范围、必需素材、明确排除项和本 Skill 不提供的修改能力，以能力说明和流程为准。

公开作者：chenyth / chenyth@gmail.com。平台依据：[Qoder 扩展上架指南](https://docs.qoder.cn/qoderwork/user-guide/qoderwork-extension-release-guide-skill-plugin-connector)。本地检查不能替代宿主实机验证或市场审核；暂不上架。
