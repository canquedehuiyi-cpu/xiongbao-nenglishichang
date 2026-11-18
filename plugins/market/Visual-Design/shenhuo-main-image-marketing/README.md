# 营销设计师 — Qoder Plugin

版本 **1.1.0**。本包仅完成本地制作与审阅准备，尚未上架；Qoder 宿主调用、服务端渠道可用性与实际审核结果仍需独立验证。

![电商主图营销包装头像](./avatars/expert.png)

## 展示资料

- Plugin 展示名称：营销设计师
- 原服务名称：电商主图营销包装
- 中文职业头衔：营销设计师
- English name: Ecommerce Main Image Marketing
- English profession: Ecommerce Main Image Marketing
- 中文简介：在现有商品主图上整理卖点、价格优惠与服务权益，保留商品身份，制作商品清楚、条件完整的营销图片。
- English description: Add organized selling points, prices and service benefits to an existing product image while preserving product identity and offer terms.

### 标签

- 主图加字 / Product Image Copy
- 价格优惠 / Prices and Offers
- 卖点包装 / Selling Point Layouts

### 快捷问题

1. 帮我给这张商品主图加上价格、商品卖点和已确认的服务信息，准确内容发给你。

   Add the exact prices, selling points and confirmed service information I provide to this product image.

2. 这张主图太满了，帮我腾出位置排好这些营销信息，商品款式和件数保持一致。

   Make room for this marketing information in the crowded image while preserving the product model and item count.

3. 只把这张主图的旧价格换成我提供的新价格，其他内容和布局保持原样。

   Replace only the old price with the new price I provide, preserving the other content and layout.

以上快捷问题与双语展示资料供人工审阅和上架表单使用；示例不代表本次用户授权，也不保证平台自动展示这些字段。

## 岗位协作

[需求整理](./skills/shenhuo-main-image-marketing-brief/SKILL.md) → [设计执行](./skills/shenhuo-main-image-marketing/SKILL.md) → [结果交付](./skills/shenhuo-main-image-marketing-delivery/SKILL.md)。三个 Skill 共用同一任务与客户端，独立触发时也读取必要流程，不依赖宿主自动注入角色文档。

外部服务、运行环境与权限见 [CONNECTORS.md](./CONNECTORS.md)。本包没有声明市场 MCP Connector。

## 服务与调用

- 插件清单：[.qoder-plugin/plugin.json](./.qoder-plugin/plugin.json)；角色入口：[qoder.md](./qoder.md)。
- 本套件内嵌 [调用 Skill](./skills/shenhuo-main-image-marketing/SKILL.md)、[能力说明](./skills/shenhuo-main-image-marketing/references/designer-profile.md)和[完整执行流程](./skills/shenhuo-main-image-marketing/references/workflow.md)。先读取这些文件，再按真实需求执行，不假定 Skill 已预加载。
- 固定调用 `des_8adee05f2e8d` / `ecommerce_main_image_marketing`（电商主图营销包装）；保留既有发布能力与默认规格，不路由或覆盖设计师身份。
- 依赖 **Python 3.10+**。发行 ZIP 内的 Python 客户端使用标准库，可独立运行，无需克隆开发仓库；源目录的轻量入口在打包时替换为完整客户端。
- 离线自检按 Skill 中的可执行检查运行，不读取凭证、不联网、不创建任务；业务调用需要网络和有效授权，只有真实回执能证明任务完成。
- 已有个人 Key 时沿用。缺 Key 时说明可选渠道体验或网站注册，取得向神火发送需求及授权素材的同意后再领取体验；不要暴露 Key，不上传未授权素材。
- 渠道 code 为 `qoder`，实际资格与积分以服务端为准。明确张数原样传递，未指定时用 auto，不额外设置试用图片数量上限。
- 神火服务完成需求理解、必要追问、创意与生成；客户端持续跟踪同一请求并下载真实结果，超时不重复建项。
- 先交付成功下载的图片，再说明未完成项与恢复方式，不要求注册才能取回已成功图片。
- 试用作品实际交付后，按 [设计执行 Skill](./skills/shenhuo-main-image-marketing/SKILL.md) 原样展示 1000 积分活动文案，再展示指定注册链接；体验项目不自动迁移。个人 Key 用户打开原账号真实项目。

## 头像与包边界

头像逐字节复用已确认的对应专家头像，位置为 [avatars/expert.png](./avatars/expert.png)。头像为 512×512 PNG、≤500KB；红色衣服胸前保留白色神火火焰及白色斜体 shenhuoai.com，不新增角标。本地头像用于审阅和上架素材，不将非规范头像字段加入插件清单。

本包只提供图片设计服务入口，不包含内部 Designer Skill 正文、生产凭证或自定义 MCP。功能范围、必需素材、明确排除项和本 Skill 不提供的修改能力，以能力说明和流程为准。

公开作者：chenyth / chenyth@gmail.com。平台依据：[Qoder 扩展上架指南](https://docs.qoder.cn/qoderwork/user-guide/qoderwork-extension-release-guide-skill-plugin-connector)。本地检查不能替代宿主实机验证或市场审核；暂不上架。
