# Changelog

支付宝开放平台 Skill(`alipay-onboarding`)发版记录。CI 构建时从本文件提取当前版本(`## X.Y.Z` 段落的下一非空行)作为 manifest 的 `changelog` 字段。

新增发版时:在顶部追加一个 `## X.Y.Z` 段落,紧随一行一句话变更摘要。

**beta 版约定(beta 内容不透出未发布 release 笔记)**:
- 正式版 `## X.Y.Z` 段落仅随 release 通道发布;beta 不会回退读取它。
- 需要给 beta 测试者看说明时,显式追加 `## X.Y.Z-beta.N` 段落(如 `## 0.0.2-beta.1`)。
- 未写 `## X.Y.Z-beta.N` 的 beta,manifest changelog 用中性占位「预发布版本 X.Y.Z-beta.N」,不泄露正式版内容。

## 0.0.7
修正小程序发布与管理 Skill 的无效文件引用，避免 Agent 读取失败。

## 0.0.6
完善小程序发布与管理流程及异常恢复指引，补充签约页面兜底、订单查询授权与防重复提交约束。

## 0.0.5
签约开通路由落地:接入 ar-sign-skill 子 Skill(个人开发者签约智能收/电脑网站/APP/JSAPI 支付的流程编排:产品推荐、资质收集、申请提交、合约/订单查询),并内置其依赖的 MCC 经营类目推荐子 Skill(mcc-recommender);主 SKILL 描述、路由 ③ 与目录结构同步更新。

## 0.0.4
优化阿宝 Skill 生产流程细节

## 0.0.3
支付宝开放平台 Skill 发布

## 0.0.3-beta.3
接入支付产品子 Skill 落地:替换原占位壳,覆盖当面付/订单码/电脑网站/手机网站/APP/JSAPI 支付及预授权、商家扣款,含产品选型、沙箱创建与多语言代码示例;沙箱操作改用本仓库 alipay-cli。

## 0.0.3-beta.2
阿宝 Skill 生产流程优化与精简;清理冗余 CLI 说明;上传后自动清理临时产物。

## 0.0.2-beta.1
调整 SKILL.md 路由内容，突出阿宝关键词；移除 cli-commands.md 部分不正确的 CLI 使用说明

## 0.0.2
供给上翻路由接入 skill-solution-scenic-generator 子 Skill(面向阿宝的模板化 Skill 生产与上架,createSkillAbility / updateSkillAbility 闭环),替换原 jinni-skill-provisioning 占位壳;主 SKILL 描述与路由 ① 意图同步更新,突出阿宝触发与 Agent 可调用确认;发布流水线支持 beta 版本(skill-vX.Y.Z-beta.N),SKILL.md version 改为 __VERSION__ 占位符、发布时按 tag 渲染,移除 frontmatter 版本校验。

## 0.0.1
首个版本:alipay-onboarding Skill 脚手架(主分发器 + 版本自检、CLI reference、两个子 skill 壳)。
