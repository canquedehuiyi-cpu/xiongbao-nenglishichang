# 线性阵列

本文档定义 CrownScript 中 `Solid.linearPattern` 的实体阵列和特征阵列约束。它是接口能力说明，不替代调用方授权；未通过 CrownCAD 实际响应或界面行为确认的组合必须标记为待验证。

## 接口

```javascript
Solid.linearPattern('线性阵列名称', {
  baseType,
  body,
  features,
  direction1,
  spacing1,
  instanceNum1,
  reverse1,
  direction2,
  hasDirection2,
  spacing2,
  instanceNum2,
  reverse2,
  patternSeed,
  skipInstance,
  instancesToSkip,
  geometryPattern
});
```

调用参数使用当前 CrownCAD 实际接口的 lower camel case 拼写。函数返回的特征对象不能猜测字段；若后续需要把返回结果作为实体输入，必须根据实际响应读取有效的 `['entityId']`。

## 阵列对象选择

`baseType` 只区分选择实体还是特征：

```text
baseType: 0
  实体阵列
  body 传入实体 ID 数组
  features 必须为 []

baseType: 1
  特征阵列
  body 必须为 []
  features 传入特征 ID 数组
```

实体阵列示例：

```javascript
Solid.linearPattern('实体线性阵列_001', {
  baseType: 0,
  body: [boxResult['entityId']],
  features: [],
  direction1: new Direction(new Point(0, 0, 0), new Point(0, 0, 1)),
  spacing1: 10,
  instanceNum1: 3,
  reverse1: 0,
  direction2: new Direction(),
  hasDirection2: 0,
  spacing2: 0,
  instanceNum2: 0,
  reverse2: 0,
  patternSeed: 0,
  skipInstance: 0,
  instancesToSkip: [],
  geometryPattern: 0
});
```

特征阵列示例：

```javascript
Solid.linearPattern('特征线性阵列_001', {
  baseType: 1,
  body: [],
  features: [bossResult['id']],
  direction1: new Direction(new Point(0, 0, 0), new Point(1, 0, 0)),
  spacing1: 15,
  instanceNum1: 3,
  reverse1: 0,
  direction2: new Direction(),
  hasDirection2: 0,
  spacing2: 0,
  instanceNum2: 0,
  reverse2: 0,
  patternSeed: 0,
  skipInstance: 0,
  instancesToSkip: [],
  geometryPattern: 0
});
```

`features` 使用源特征接口返回的特征 `['id']`，不是源实体的 `['entityId']`。特征必须是已经附着在实体上的可阵列特征；独立基体或不属于实体特征树的对象可能返回成功但不生成可见阵列。

## 方向、间距和实例数

### 方向引用

第一方向和第二方向都使用 `Direction`：

```javascript
new Direction(existingDirectionId)
new Direction(new Point(0, 0, 0), new Point(0, 0, 1))
```

已有草图直线、边线、基准线或方向 ID 时使用真实引用。使用两点创建方向时两点必须不同；不需要手动归一化。

### 间距

```text
0.00001 mm ≤ spacing1 ≤ 10000000 mm
0.00001 mm ≤ spacing2 ≤ 10000000 mm
```

启用的方向不能使用 `0` 或负数间距。`spacing2` 在第二方向关闭时使用占位值 `0`。

`spacing1`、`spacing2` 是长度参数；只有本文件参数表将其支持类型写成包含 `Variable` 时，才允许传入长度变量。`instanceNum1`、`instanceNum2` 是实例数量参数；本次 `instanceNum1` 的数字变量调用未产生类型错误，但结果为 `entityId: 0`，因此不能视为已验证的变量参数。

### 实例数与反向

第一方向的 `instanceNum1` 包含源实体，通常至少为 `2`。启用第二方向时，`instanceNum2` 也包含源位置，使用有效实例数，通常至少为 `2`；第二方向关闭时使用占位值 `0`。

```text
reverse1: 0 正向，1 反向
reverse2: 0 正向，1 反向
```

`reverse1` 和 `reverse2` 分别控制对应方向，不要把它们当作角度或布尔值以外的枚举。

## 第二方向和阵列源

```text
hasDirection2: 0
  只生成第一方向阵列
  direction2 可使用 new Direction()
  spacing2、instanceNum2 使用 0 占位

hasDirection2: 1
  启用第二方向
  必须提供有效 direction2、spacing2 和 instanceNum2
```

`patternSeed` 对应界面的“只阵列源”选项：

```text
patternSeed: 0  默认阵列方式
patternSeed: 1  只用源对象生成第二方向阵列
```

`patternSeed:1` 的最终组合数量和与跳过实例的交互，应以具体 CrownCAD 版本的执行结果为准；当前项目将其作为已识别的界面参数，但不把未实测的边界行为写死。

## 跳过实例

```text
skipInstance: 0  不启用跳过
skipInstance: 1  启用跳过
```

`instancesToSkip` 使用字符串形式的二元组，两个编号都从 `1` 开始，顺序固定为：

```text
(第一方向实例序号, 第二方向实例序号)
```

第二方向关闭时，第二个编号固定为 `1`：

```javascript
skipInstance: 1,
instancesToSkip: ['(2,1)', '(3,1)']
```

第二方向开启时，例如：

```javascript
skipInstance: 1,
instancesToSkip: ['(1,2)', '(1,3)', '(2,1)']
```

表示分别跳过指定的方向组合位置。编号不是零基索引；无效、重复或超出实例数的项必须在执行前校验或标记为待验证。

## geometryPattern

`geometryPattern` 只用于特征阵列，不改变 `baseType` 的实体/特征选择含义：

```text
baseType: 0  实体阵列时保持 geometryPattern: 0
baseType: 1  特征阵列时传 geometryPattern: 0 或 1
```

按 SolidWorks/CrownCAD 的同类语义：

```text
geometryPattern: 0  普通特征阵列，按特征逻辑重新求解
geometryPattern: 1  几何阵列，复制几何结果，减少对特征逻辑的重新求解
```

对简单凸台或简单切除，两种模式可能看起来完全相同；差异通常要在带终止面、复杂依赖或特征求解代价明显的特征上观察。当前项目不根据肉眼无差异就删除该参数，也不把 `geometryPattern` 当作实体阵列/特征阵列的选择开关。

## 生成和校验约束

- 变量声明只能使用 `var`。
- 特征名称必须唯一、非空且可读，使用中文语义名称。
- `baseType:0` 时强制校验 `features.length === 0`；`baseType:1` 时强制校验 `body.length === 0`。
- `body` 只能放实体 `['entityId']`；`features` 只能放源特征 `['id']`。
- 间距、实例数、方向引用和 `reverse` 值必须按启用状态校验。
- `instancesToSkip` 只有在 `skipInstance:1` 时生效，按 1 基编号和 `(方向1,方向2)` 顺序生成。
- 所有函数参数、对象和数组末项禁止尾随逗号；每条可执行语句必须以英文半角分号结束。
- 阵列后续若需要实体操作，只能使用阵列成功响应中的当前 `['entityId']`；不能继续使用已被阵列特征替换或失效的源实体 ID。

## 执行工作流

- 线性阵列作为一个语义完整的建模阶段提交。
- 固定文档上下文，维护完整源码；正常新增默认追加，例外按[执行流程](../../execution-workflow.md)处理。
- 阵列本身通常不需要拓扑查询；只有后续操作需要当前面、边或点时，才在阵列成功后重新采集当前拓扑。
- 阶段失败按主执行流程判断实际状态后修正或评估重建；同步完整源码，最多 3 次自动修正是上限，不要求试满。

## 变量兼容性验证

在用户提供的 PartDocument 上，实体线性阵列分别使用长度变量作为 `spacing1`、数字变量作为 `instanceNum1`，特征线性阵列使用长度变量作为 `spacing1`，三次调用均未返回 `errorInfo`。但三次返回的阵列结果 `entityId` 均为 `0`，所以目前只能记录为接口层未报类型错误，不能宣称线性阵列几何结果已经验证成功。`direction`、`reverse`、`baseType`、`body`、`features` 和其他 ID/枚举参数仍不能用变量替代。
