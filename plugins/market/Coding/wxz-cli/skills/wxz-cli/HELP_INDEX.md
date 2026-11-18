# 万小智帮助文档索引与要点

> 整理自阿里云帮助中心：[AI 建站万小智](https://help.aliyun.com/zh/product/3039206.html)。
> 官方文档持续更新，建议结合 `SKILL.md` 中的动态获取方式定期核对。

## 动态获取文档

获取最新文档目录：

```bash
curl 'https://help.aliyun.com/help/json/menupath.json?nodeId=3039206&website=cn&language=zh&channel='
```

返回 JSON 的 `data.children` 为文档树。单篇文章完整 URL：

```text
https://help.aliyun.com/zh/document_detail/{id}.html
```

其中 `{id}` 替换为 JSON 中的 `id` 字段。

## 完整文档索引

| 模块 | 文档标题 | 文章 ID | URL |
|------|----------|---------|-----|
| 产品概述 | 什么是万小智 2.0 | 3039522 | https://help.aliyun.com/zh/document_detail/3039522.html |
| 产品概述 | 产品计费 | 3039523 | https://help.aliyun.com/zh/document_detail/3039523.html |
| 快速入门 | 创建你的第一个应用 | 3039524 | https://help.aliyun.com/zh/document_detail/3039524.html |
| 快速入门 | 创建你的第一个小程序 | 3041447 | https://help.aliyun.com/zh/document_detail/3041447.html |
| 功能介绍 | 应用编辑 | 3039526 | https://help.aliyun.com/zh/document_detail/3039526.html |
| 功能介绍 | 内容管理 | 3039527 | https://help.aliyun.com/zh/document_detail/3039527.html |
| 功能介绍 | 应用发布 | 3039528 | https://help.aliyun.com/zh/document_detail/3039528.html |
| 后台管理 | 数据洞察 | 3041874 | https://help.aliyun.com/zh/document_detail/3041874.html |
| 后台管理 | 创意中心 | 3039530 | https://help.aliyun.com/zh/document_detail/3039530.html |
| 后台管理 | 插件服务 | 3039531 | https://help.aliyun.com/zh/document_detail/3039531.html |
| 后台管理 | 密钥管理 | 3039534 | https://help.aliyun.com/zh/document_detail/3039534.html |
| 后台管理 | 应用工具 | 3039533 | https://help.aliyun.com/zh/document_detail/3039533.html |
| 后台管理 | 通知配置 | 3041873 | https://help.aliyun.com/zh/document_detail/3041873.html |
| 后台管理 | 域名管理 | 3039529 | https://help.aliyun.com/zh/document_detail/3039529.html |
| 后台管理 | SEO 管理 | 3039535 | https://help.aliyun.com/zh/document_detail/3039535.html |
| 后台管理 | 回收站 | 3039536 | https://help.aliyun.com/zh/document_detail/3039536.html |
| 常见问题 | 售后服务方式 | 3039541 | https://help.aliyun.com/zh/document_detail/3039541.html |
| 常见问题 | 业务相关 FAQ | 3039542 | https://help.aliyun.com/zh/document_detail/3039542.html |
| 常见问题 | 功能相关 FAQ | 3039543 | https://help.aliyun.com/zh/document_detail/3039543.html |
| 常见问题 | 操作相关 FAQ | 3039544 | https://help.aliyun.com/zh/document_detail/3039544.html |

## 核心要点速览

### 计费与版本

- 费用由「版本订阅费 + 灵感值资源包」组成，均为预付费。
- Web 版本（中国内地节点）：轻量版 360 元/年、标准版 980 元/年、高级版 1980 元/年。
- 1 灵感值 = 0.01 元；首次使用赠送 2000 灵感值。
- 常见消耗：AI 应用开发约 70 灵感值/轮、AI 生图 20 灵感值/张、多语言翻译 10 灵感值/千字。
- 新购后 5 天内支持无理由退款；灵感值资源包不支持退款。
- 应用过期后无法访问，到期数据保留 15 天，超期未续费将释放。

### 发布与部署

- 首次发布必须购买版本；中国内地节点需完成 ICP 备案才能通过域名访问。
- 中国香港节点无需备案，但国内访问可能延迟较高；购买后支持内地升级至香港，不支持反向迁移。
- 发布通常需要 1~5 分钟；发布后需绑定域名才能公网访问。

### 域名与 HTTPS

- 一个网站可绑定多个域名；系统会自动添加带 `www` 前缀的域名。
- 阿里云账号下的域名支持一键解析；其他域名需手动添加 CNAME/TXT 记录。
- 默认提供一键 HTTPS 证书，有效期 90 天，到期前自动续期。
- 中文域名需转换为 Punycode 后绑定，且不支持 CDN 和 HTTPS。

### 内容管理与数据

- 预置数据表：文章管理、产品管理。
- 支持 AI 自定义数据表，通过自然语言描述字段需求自动生成。
- 删除的内容进入回收站，保留 30 天后自动永久清除。

### 插件与扩展能力

- 插件：高德地图、阿里云视频、支付宝支付、文本/图片/视频生成大模型、OCR。
- 支付宝支付需扫码授权支付宝商户应用，一个支付宝应用只能授权给一个服务商。
- 调用外部服务所需 API Key 通过「密钥管理」集中保管，不在代码中明文存储。

### 后台工具

| 工具 | 说明 |
|------|------|
| 数据统计 | 查看 PV/UV、总会话数、检索记录等网站访问数据。 |
| 智能问答 | 7×24 智能客服，支持知识库管理。 |
| 智能翻译 | 标准版及以上可用，多语言页面首次访问时消耗灵感值。 |
| 数据洞察 (ChatBI) | 自然语言生成数据报表，需先开启且有业务数据。 |
| 创意中心 | 素材管理、AI 生图/修图、Logo 制作、背景替换等。 |
| 插件服务 | 高德地图、阿里云视频、支付宝支付、文本/图片/视频生成大模型、OCR。 |
| 密钥管理 | 集中保管调用第三方 API 所需的 API Key，加密存储。 |
| 通知配置 | 短信/邮箱通知数据变更；内置手机号/邮箱登录验证码场景。 |
| SEO 管理 | 百度/Bing/Google 站点验证、Sitemap 自动生成。 |
| 回收站 | 集中管理内容管理模块删除的数据，保留 30 天。 |
