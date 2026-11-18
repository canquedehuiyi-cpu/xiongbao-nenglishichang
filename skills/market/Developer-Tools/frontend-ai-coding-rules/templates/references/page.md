# 页面层分册

入口在同目录上一级的 `AGENTS.md`（§7 分册索引）。

<!-- 填写指引：本册每节的骨架示例，贴【本技能 references/discovery.md §3.1 判出的那一档】在本仓库的真实代码，不是通用最佳实践。
     A 档贴封装用法；B 档贴组件库裸用的最小可用写法（分页 / 排序 / 列显隐各自怎么写）；
     C 档（项目没有这个概念）不写空壳，改写「替代做法」：列表是卡片 / 树 / 路由页时按那个形态贴代码。 -->新建或改造列表页 / 搜索区 / 弹窗抽屉 / 树表时按小节读。禁止事项、验证矩阵与交付自检在入口 §8-§10。



## 1. 页面骨架

```vue
{{粘贴本项目最标准的一段 index.vue：script setup 头部 + 表格/列表配置 + template 结构}}
```

硬性要求：
- `<script setup lang="ts">`（`{{是否需要 name/defineOptions}}`）。
- 页面容器：`{{Page 或等价壳}}`。
- 列表：`{{表格组件 + 默认配置函数}}`，`{{必须存在的配置项}}`。
- 数据获取：`{{proxyConfig / onMounted 请求 / 分页合并方式}}`。
- 工具栏与操作列插槽：`{{实际插槽名}}`。
- 加载态：`{{本项目 loading 方式}}`。

## 2. 搜索区

- 组织方式：`{{独立组件 | 内联 | schema}}`。
- 栅格 / 样式类：`{{如 tableSeachClass}}`。
- 与父页面的契约：`{{defineExpose({ getValues, resetFields }) | props/emit 约定}}`。
- 提交与重置语义：`{{reload(values) 回第一页 / query() 留当前页}}`。
- 回车提交、折叠展开、日期区间拆分：`{{本项目实际写法}}`。

## 3. 新增 / 编辑弹窗（抽屉）

- 父页面接入：`{{如 useVbenModal/useVbenDrawer({ connectedComponent }) + setData + open}}`。
- 子组件生命周期：`{{如 onOpenChange 取 getData、onConfirm、onClosed 重置}}`。
- 表单：`{{schema 驱动 | 手写 Form + validate}}`；校验规则 `{{类型}}`。
- 提交流：`{{lock → validate → cloneDeep → add/update → emit('reload') → close → unlock}}`。
- 脏数据离开拦截：`{{方案}}`（无则 `不适用`）。
- Modal / Drawer / 独立路由页 的选择依据：`{{本项目习惯}}`。

## 4. 树表 / 树筛选（按需保留）

- 接口返回：`{{数组 | PageResult}}`。
- 组树：`{{如 listToTree / 后端直接返回树}}`。
- 表格树配置：`{{如 treeConfig + keyField}}`；展开控制：`{{方案}}`。
- 上级选择组件：`{{组件名}}`；新增子节点带入 `parentId` 的方式：`{{写法}}`。
