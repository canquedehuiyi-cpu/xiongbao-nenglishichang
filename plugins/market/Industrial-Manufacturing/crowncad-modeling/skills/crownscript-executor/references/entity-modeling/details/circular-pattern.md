# 圆周阵列

本文档定义 CrownScript 中 `Solid.circularPattern` 的实体阵列和特征阵列参数约束。它是接口能力说明，不替代调用方授权，也不代表尚未实测的参数组合已经在 CrownCAD 服务端执行成功。

## 接口

```javascript
Solid.circularPattern('圆周阵列名称', {
  baseType,
  body,
  features,
  axis,
  reverse,
  angle1,
  instanceNum1,
  equalSpacing1,
  symmetric,
  hasDirection2,
  angle2,
  instanceNum2,
  equalSpacing2,
  skipInstance,
  instancesToSkip
})
```

接口返回圆周阵列特征信息。若后续需要把返回值作为实体输入，必须先以实际响应确认返回对象中的有效实体字段；不得猜测返回对象结构。

## 阵列对象选择

`baseType` 只区分选择实体还是特征：

```text
baseType: 0
  实体阵列
  使用 body 传入一个实体 ID
  features 使用空列表 []

baseType: 1
  特征阵列
  使用 features 传入特征 ID 列表
  body 不参与选择
```

自然语言映射只需要区分实体和特征，不把 `geometryPattern` 暴露为另一种用户级阵列模式。若底层接口在特征阵列执行时仍要求该字段，必须在实际接口验证后再补充其兼容性传值。

## 阵列轴

### 新建世界 Y 轴

项目的世界“上方”为 `+Y`。过原点的世界 Y 轴可表示为：

```javascript
new Axis(new Point(0, 0, 0), new Point(0, 1, 0))
```

两个点必须不同。

### 使用已有直线

使用已有直线作为轴时传入真实 `lineId`：

```javascript
new Axis(lineId)
```

不得把该直线的 `entityId` 当作 `lineId` 传入。若轴来自后续拓扑选择，必须使用当前有效的真实引用。

## 角度和方向

```text
0.001° ≤ angle1 ≤ 360°
0.001° ≤ angle2 ≤ 360°
```

角度以度为单位，不能传入零角度或超过 360° 的值。

`angle1`、`angle2` 是角度参数；只有本文件参数表将其支持类型写成包含 `Variable` 时，才允许传入角度变量。`instanceNum1`、`instanceNum2` 是实例数量参数，本次数字变量调用未产生类型错误，但返回结果仍需以有效实体或特征 ID 确认。

```text
reverse: 0 逆时针
reverse: 1 顺时针
```

第二方向没有独立的 `reverse2`。启用第二方向时，第二方向固定为第一方向的相反方向；`reverse` 改变这对方向的整体朝向。

## 实例数量

```text
instanceNum1 ≥ 2
instanceNum2 ≥ 2
```

实例数包含源实体。

按当前已确认的界面规则：

```text
未启用第二方向：
  总实例数 = instanceNum1

启用第二方向：
  总实例数 = instanceNum1 + instanceNum2 - 1

启用两侧对称：
  总实例数 = 2 × instanceNum1 - 1
```

这些是当前参数映射约束。真正执行新的参数组合时，仍需检查服务端响应，不能只凭公式宣称模型成功。

## 等间距

```text
equalSpacing1: 0 不启用第一方向等间距
equalSpacing1: 1 启用第一方向等间距

equalSpacing2: 0 不启用第二方向等间距
equalSpacing2: 1 启用第二方向等间距
```

跳过实例不会重新计算或压缩剩余实例的角度位置；被跳过的位置仍处于原等间距序列中。

## 对称和第二方向

两种模式互斥：

```text
symmetric: 1
  启用两侧对称
  不启用方向2
  不设置 angle2、instanceNum2、equalSpacing2

hasDirection2: 1
  启用第二方向
  symmetric 必须为 0
  设置 angle2、instanceNum2、equalSpacing2
```

不能同时提交：

```javascript
{
  symmetric: 1,
  hasDirection2: 1
}
```

## 跳过实例

启用跳过功能：

```javascript
skipInstance: 1
```

跳过列表使用字符串形式的二元组：

```javascript
instancesToSkip: ['(第一方向实例序号,第二方向实例序号)']
```

两个方向的实例序号均从 `1` 开始。

### 启用第二方向

二元组顺序固定为：

```text
(第一方向实例序号, 第二方向实例序号)
```

例如：

```javascript
instancesToSkip: ['(1,2)', '(1,3)', '(1,5)', '(1,7)', '(1,8)']
```

表示第一方向第 `1` 个位置下，跳过第二方向的第 `2、3、5、7、8` 个位置。

### 未启用第二方向

第二个编号固定为 `1`：

```javascript
instancesToSkip: ['(2,1)', '(3,1)']
```

表示跳过第一方向第 `2` 和第 `3` 个位置。

跳过后的实际生成数量等于名义总实例数减去有效跳过项数量。跳过源实体是否被允许、重复跳过项如何处理，若任务涉及这些边界情况，必须先通过实际接口验证。

## CrownScript 生成约束

- 变量声明只能使用 `var`。
- 特征名称必须唯一、非空且可读，使用中文语义名称。
- `body`、`features`、`axis` 和所有实例参数必须来自已确认的真实输入；不得猜测实体 ID、特征 ID、`lineId` 或轴引用。
- 函数参数、对象和数组末项不得有尾随逗号。
- 每条可执行语句必须以英文半角分号结束。
- 圆周阵列若作为后续实体特征的输入，必须先根据真实执行响应确认其有效返回引用；后续圆角、倒角或实体操作不得继续使用已失效的输入实体 ID。

## 执行工作流

- 圆周阵列作为一个语义完整的建模阶段提交。
- 固定文档上下文，维护完整源码；正常新增默认追加，例外按[执行流程](../../execution-workflow.md)处理。
- 圆周阵列本身通常不需要拓扑查询；只有后续操作需要当前面、边或点时，才在阵列成功后重新采集当前拓扑。
- 阶段失败按主执行流程判断实际状态后修正或评估重建；同步完整源码，最多 3 次自动修正是上限，不要求试满。
- 当前文档与参数规则来自接口说明和用户提供的界面行为；未经 CrownCAD 实际响应验证的组合必须标记为待验证。

## 变量兼容性验证

在用户提供的 PartDocument 上，实体圆周阵列使用角度变量作为 `angle1`、数字变量作为 `instanceNum1`，特征圆周阵列使用角度变量作为 `angle1`，三次调用均未返回 `errorInfo`。但三次返回的阵列结果 `entityId` 均为 `0`，所以目前只能记录为接口层未报类型错误，不能宣称圆周阵列几何结果已经验证成功。`axis`、`reverse`、`baseType`、`body`、`features` 和其他 ID/枚举参数仍不能用变量替代。
