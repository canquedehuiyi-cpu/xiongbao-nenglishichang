# QODERWORK.md — 超级数仓工程师套件配置

> 本文件为团队配置模板。复制到项目目录后按需修改，Agent 会读取并遵循其中的规范。

---

## 1. 团队命名规范

### 表命名

```
{数据层}_{业务域}_{实体}_{粒度}

数据层: ods | dwd | dws | ads | dim | tmp
业务域: order | user | product | finance | ...
实体: 具体业务对象
粒度: df (日全量) | di (日增量) | hf (小时全量) | hi (小时增量) | mf (月全量)

示例:
- dwd_order_detail_di
- dws_user_active_df
- ads_finance_revenue_mf
```

### 节点命名

```
{业务域}_{数据层}_{表名}

示例:
- 订单_dwd_明细清洗
- 用户_dws_活跃统计
```

### 字段命名

- 使用英文小写 + 下划线
- 时间字段：`gmt_create`, `gmt_modified`
- 分区字段：`ds`, `hh`
- 状态字段：动词 + 状态，如 `is_deleted`, `has_paid`

---

## 2. SQL 风格

### 格式

- 关键字大写：`SELECT`, `FROM`, `WHERE`, `JOIN`
- 表名/字段名保持原样
- 缩进：4 个空格
- 每行一个主要子句

### 示例

```sql
SELECT
    user_id,
    order_id,
    gmt_create
FROM dwd_order_detail_di
WHERE ds = '${bizdate}'
    AND is_deleted = 'N'
```

---

## 3. 资源组配置

| 环境 | 资源组标识 | 用途 |
|------|-----------|------|
| 默认调度 | {group_xxx} | 常规 ODPS SQL 任务 |
| DI 同步 | {group_xxx} | 数据集成任务 |
| 高优先级 | {group_xxx} | 基线关键任务 |

---

## 4. 工作空间映射

| 业务线 | 工作空间名 | 工作空间 ID |
|--------|-----------|------------|
| 示例业务 | example_project | 12345 |

---

## 5. 发布规范

- 开发环境验证通过后才能发布
- 生产环境发布需人工确认
- 涉及 DDL 变更需 DBA 审批
- 新节点发布后当天需手动补数据验证

---

## 6. 数据质量规则

- 核心表必须配置 DQC 规则
- 行数波动阈值：±20%
- 主键唯一性：100%
- 空值率：核心字段 < 1%

---

*根据团队实际情况修改以上配置*
