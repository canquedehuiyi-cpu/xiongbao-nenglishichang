# Common 变量管理与表达式

## 1. 模块描述

Common 变量模块提供当前文档级的变量管理和表达式计算能力。变量不依赖草图；草图、实体、装配或其他业务模块只有在接口明确支持变量时，才能消费当前文档中的变量。

本文件是 Common 变量模块的唯一规则入口，负责说明模块边界、通用前置条件、变量生命周期命令、表达式规则和跨模块使用限制。

## 2. 能力定位与边界

### 2.1 职责范围

Common 变量模块负责：

- 创建当前文档中的变量；
- 修改变量的名称、表达式、类型、单位和描述；
- 删除不再被引用的变量；
- 计算变量表达式并维护变量依赖；
- 为其他模块提供变量引用。

### 2.2 模块边界

- 变量属于当前文档上下文，不依赖草图。
- 变量查询接口暂未纳入当前规则。后续若提供“查询当前文档全部变量”接口，再补充到本文件。
- Common 变量模块不负责创建草图、实体或装配特征。
- 其他模块只能在其接口参数表的支持类型中包含 `Variable` 时使用变量对象；不能因为参数是浮点型或数值型，就默认它支持变量。

区分脚本参数修改后完整重建与 CAD 原生变量/尺寸关联驱动。仅在接口明确支持且实际建立、验证了关联时，才声称可原生驱动；导入实体、计算得到的草图坐标或返回参数对象都不自动具有这种能力。不支持变量引用的参数应如实标为本地计算重建，不用伪约束补齐。

## 3. 前置约束

### 3.1 文档上下文

- 变量必须存在于当前 CrownCAD 文档中。
- 表达式引用的变量必须已经在当前文档中创建。
- 创建变量使用待创建的新变量名；修改和删除使用当前已有变量名。
- 当前变量不存在时不能直接修改或删除。

### 3.2 命名与描述

- 同一文档内的变量名必须唯一。
- 变量名、`newName` 和 `variableDescription` 只能使用英文或 ASCII 文本，不能使用中文。
- 被其他变量引用的变量不得改名或删除。

### 3.3 类型与单位

变量类型只有：

```javascript
VariableType.Length
VariableType.Angle
VariableType.Number
```

单位对应关系为：

```text
Length -> mm / cm / m
Angle  -> degree / radian
Number -> number
```

`Length`、`Angle` 和 `Number` 之间不允许混合运算。`variableExpression`、`variableType` 和 `variableUnit` 必须相互匹配。

### 3.4 表达式规则

`variableExpression` 是表达式字符串。当前已确认支持：

- 数值字面量，例如 `'80'`；
- 引用当前文档中之前创建的变量；
- 单引号变量引用，例如 `'tets'`；
- `+`、`-`、`*`、`/`；
- 括号；
- 比较运算符，例如 `=`、`<`、`>`、`<=`、`>=`；
- `if` 条件表达式；
- 以下函数和常量：

```text
sin cos tan cot sec csc
asin acos atan acot asec acsc
sinh cosh tanh coth sech csch
asinh acosh asech acoth acsch
sqrt abs exp log10 pi if
```

三角函数按角度计算，已确认：

```text
sin(90) = 1
```

条件表达式格式为：

```text
if(条件, 条件成立时的值, 条件不成立时的值)
```

例如：

```javascript
Common.createVariable('test1', {
  variableExpression: "if('tets' > 5, 100, 0)",
  variableType: VariableType.Number,
  variableUnit: VariableUnit.number
});
```

`if` 不支持嵌套。

当前不支持引用：

- 尺寸；
- 文件属性；
- 测量值；
- 其他方程式。

### 3.5 依赖关系

被引用变量必须先创建，脚本应按依赖顺序排列：

```text
tets -> test1 -> test2
```

例如，`test1` 引用 `tets` 时，必须先创建 `tets`：

```javascript
Common.createVariable('tets', {
  variableExpression: '5',
  variableType: VariableType.Number,
  variableUnit: VariableUnit.number
});

Common.createVariable('test1', {
  variableExpression: "('tets' * 2) + 5",
  variableType: VariableType.Number,
  variableUnit: VariableUnit.number
});
```

这里 `tets` 的值为 `5`，`test1` 的值为 `15`。修改 `tets` 后，`test1`、`test2` 等下游变量必须立即重新计算。

### 3.6 变量对象使用前提

只有接口文档的支持类型中包含 `Variable` 时，才允许传递 `new Variable(...)`。其中 `Number | Variable` 表示普通数值或变量均可，`Variable` 表示必须传入变量。变量对象可以通过常量或已有变量名构造：

```javascript
var constantRef = new Variable(100);
var variableRef = new Variable('tets');
```

不能仅因为目标参数是浮点型或数值型，就默认传入变量对象。

## 4. 命令说明

### 4.1 命令总览

| 命令 | 用途 | 返回值 |
| --- | --- | --- |
| `Common.createVariable` | 创建当前文档变量 | 实测为 `None` |
| `Common.assignVariable` | 修改变量名称、表达式、类型、单位或描述 | 当前规则不依赖返回对象 |
| `Common.deleteVariable` | 删除当前文档中未被引用的变量 | 当前规则不依赖返回对象 |

### 4.2 创建变量：`Common.createVariable`

```javascript
Common.createVariable('tets', {
  variableExpression: '5',
  variableType: VariableType.Number,
  variableUnit: VariableUnit.number,
  variableDescription: 'test variable'
});
```

参数和规则：

- 第一个参数是新变量名，必须唯一；
- `variableExpression` 必须传递；
- `variableType` 必须传递；
- `variableUnit` 必须传递；
- `variableDescription` 可以省略；
- 变量名和描述只能使用英文或 ASCII 文本；
- 创建接口返回值实测为 `None`，不能从返回值读取变量对象。

### 4.3 修改变量：`Common.assignVariable`

```javascript
Common.assignVariable('tets', {
  newName: 'testNew',
  variableExpression: '90',
  variableType: VariableType.Number,
  variableUnit: VariableUnit.number,
  variableDescription: 'updated variable'
});
```

参数和规则：

- 第一个参数是当前变量名，必须存在；
- `newName` 可以省略或传空字符串，表示不改名；
- 传递 `newName` 时，新名称必须唯一，并只能使用英文或 ASCII 文本；
- `variableExpression` 必须传递；
- `variableType` 必须传递；
- `variableUnit` 必须传递；
- `variableDescription` 可以省略，传递时只能使用英文或 ASCII 文本；
- 被其他变量引用时，不允许改名；
- 修改被引用变量后，所有依赖变量立即重新计算。

不修改名称时：

```javascript
Common.assignVariable('tets', {
  variableExpression: '90',
  variableType: VariableType.Number,
  variableUnit: VariableUnit.number
});
```

### 4.4 删除变量：`Common.deleteVariable`

```javascript
Common.deleteVariable('tets');
```

参数和规则：

- 参数是当前变量名，必须存在；
- 被其他变量引用时，不允许删除；
- 不接收配置对象；
- 不涉及 `variableDescription`。

### 4.5 构造变量引用：`new Variable`

`new Variable(...)` 只构造供其他明确支持变量的接口读取的引用，不会创建新的文档变量：

```javascript
var constantRef = new Variable(100);
var variableRef = new Variable('tets');
```

变量引用的具体参数类型和限制由对应模块的接口文档说明，Common 文档不重复维护其他模块的参数清单。

## 5. 执行注意事项

### 5.1 覆盖与追加执行

- 执行覆盖会清空旧文档变量；
- 执行追加会保留当前文档变量；
- 覆盖模式下，累计脚本必须重新创建本阶段需要的全部变量；
- 追加模式下，可以继续使用当前文档中已经存在的变量。

### 5.2 脚本生成与错误处理

- 变量创建必须先于依赖它的变量；
- 同一脚本内变量名必须唯一；
- 对已被引用的变量，不生成改名或删除调用；
- `variableExpression`、`variableType`、`variableUnit` 必须与变量的类型保持一致；
- 变量名、`newName` 和 `variableDescription` 统一使用英文或 ASCII 文本；
- 所有 CrownScript 变量声明只能使用 `var`；
- 对象字面量和数组末项不得使用尾随逗号；
- 创建、修改和删除接口的具体错误应优先根据返回的错误信息分析，不随机改写表达式。
