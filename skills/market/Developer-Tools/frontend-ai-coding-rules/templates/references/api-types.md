# API 与类型分册

入口在同目录上一级的 `AGENTS.md`（§7 分册索引）。写 API 函数、类型定义或决定文件落位时读本册。禁止事项、验证矩阵与交付自检在入口 §8-§10。

## 1. 目录与命名映射

- 后端 `{{backend-prefix}}/<module>/<business>/*` ↔ 前端 `{{api-dir}}/<module>/<business>/*` + `{{views-dir}}/<module>/<business>/*`
- 模块文件构成（按本项目实际保留）：
  - `index.vue` —— 列表页 / 页面入口
  - `<business>-search.vue` —— 搜索区（按需保留）
  - `<business>-modal.vue` / `<business>-drawer.vue` —— 新增编辑（按需保留，二选一）
  - `<business>-detail.vue` / `-view-drawer.vue` —— 详情（按需保留）
  - `data.ts` / `data.tsx` —— 列定义与表单 schema
- 命名约定：`{{文件 kebab-case / 组件 PascalCase / API 动词}}`
- 路由：`{{是否需要手工注册；动态路由 component 映射规则；meta 字段清单}}`

## 2. API 层规则

- 文件位置：`{{api-dir}}/<module>/<business>/index.ts`，类型同目录 `{{type-file-name}}`。
- import 顺序跟随相邻文件：
  ```ts
  {{真实 api 文件的 import 块}}
  ```
- 请求统一走 `{{http-instance}}`，禁止另起实例或裸 fetch。
- 返回类型：分页 `{{写法}}`；详情 `{{写法}}`；树表 `{{写法}}`。
- 函数命名：`{{本项目实际动词表：listXxx 或 xxxList 等}}`。
- 接口前缀：`{{enum / 常量 / 内联字符串}}`。
- 参数：`{{params / data 传法与序列化约定}}`。
- 成功提示：`{{WithMsg 类方法或手动 message}}`；导出走 `{{export-helper}}`。
- 加密 / 特殊 header：`{{场景}}`（无则 `不适用`）。

## 3. 类型层规则

- 实体类型：`{{文件与命名规则}}`，字段保留后端注释。
- 公共类型来源：`{{ID / PageQuery / PageResult / BaseEntity 路径}}`。
- 主键类型 `{{实际约定}}`；批量入参 `{{约定}}`。
- Java/后端类型映射：`{{数值、Boolean、日期落到什么}}`。
- 表单态：`{{如 Partial<Entity> + getDefaultValues()}}`；查询参数：`{{约定}}`。
- 校验规则类型：`{{如 AntdFormRules<T> / RulesForm}}`。
- 能收窄就不写 `any`；无法收窄时保留并注明原因。
