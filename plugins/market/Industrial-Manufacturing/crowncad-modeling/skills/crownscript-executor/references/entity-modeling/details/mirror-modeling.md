# CrownCAD 镜像建模

本文档说明 `Solid.mirrorSolid` 的实体镜像和特征镜像。

## 基本规则

| 内容 | 正确用法 |
|---|---|
| 实体镜像对象 | `result['entityId']` |
| 特征镜像对象 | `result['id']` |
| 镜像结果实体 | `mirrorResult['entityId']` |
| 镜像结果特征 | `mirrorResult['id']` |
| 镜像平面 | 真实的基准面 ID 或实体平面 ID |

- 变量只能使用 `var`。
- 特征名必须唯一、非空、可读。
- CrownScript 不使用尾随逗号。
- 所有尺寸单位为 mm；镜像本身没有尺寸参数。
- `geometryPattern` 暂不支持，不传入该参数。
- 没有真实的镜像平面 ID 时，不执行，也不猜测 ID。

## 实体镜像：`baseType: 0`

`body` 必须是真实的实体 `entityId`。

```javascript
var sourceEntityId = sourceResult['entityId'];

var mirrorResult = Solid.mirrorSolid('实体镜像_001', {
    baseType: 0,
    body: sourceEntityId,
    mirrorPlane: mirrorPlaneId,
    mergeSolids: 0
});

var mirrorEntityId = mirrorResult['entityId'];
```

## 特征镜像：`baseType: 1`

`features` 必须使用特征 ID，也就是前序特征结果中的 `result['id']`，不能使用 `result['entityId']`。

### 单个特征

```javascript
var sourceFeatureId = featureResult['id'];

var featureMirrorResult = Solid.mirrorSolid('特征镜像_001', {
    baseType: 1,
    features: [sourceFeatureId],
    mirrorPlane: mirrorPlaneId,
    mergeSolids: 0
});

var featureMirrorId = featureMirrorResult['id'];
var featureMirrorEntityId = featureMirrorResult['entityId'];
```

### 多个特征

多个特征默认必须属于同一个 Body。

```javascript
var firstFeatureId = firstFeatureResult['id'];
var secondFeatureId = secondFeatureResult['id'];

var multiFeatureMirrorResult = Solid.mirrorSolid('多特征镜像_001', {
    baseType: 1,
    features: [firstFeatureId, secondFeatureId],
    mirrorPlane: mirrorPlaneId,
    mergeSolids: 0
});

var multiFeatureMirrorId = multiFeatureMirrorResult['id'];
var multiFeatureMirrorEntityId = multiFeatureMirrorResult['entityId'];
```

## `mergeSolids` 生命周期

`mergeSolids: 0`：

- 原实体继续有效；
- 镜像结果是新实体；
- 后续实体操作可以使用原实体或 `mirrorResult['entityId']`。

`mergeSolids: 1`：

- 参与合并的原实体失效；
- 镜像后得到新的合并实体；
- 后续实体操作必须使用新的 `mirrorResult['entityId']`。

镜像接口中的 `mergeSolids` 是整数开关 `0/1`，不是实体 ID 数组。

## 变量兼容性

镜像接口本身没有尺寸参数。`baseType`、`mergeSolids`、`body`、`features` 和 `mirrorPlane` 分别是整数开关、整数开关或实体/特征/平面 ID，不能用 `Variable` 替代。实测将 `new Variable(...)` 传给 `mergeSolids` 时，服务端返回“`mergeSolids` 应为 Integer”。

在用户提供的 PartDocument 上，实体镜像的普通参数调用未返回 `errorInfo`，但结果 `entityId` 为 `0`；因此本次只确认了参数类型边界，镜像几何结果仍待验证。

## 镜像平面

允许两类镜像平面：

- 基准面 ID；
- 实体平面 ID。

实体平面 ID 必须来自当前有效拓扑。任何成功的几何操作后，旧的实体平面 ID 都不能继续作为可靠引用，下一阶段需要重新查询。

基准面创建和基准面专用查询接口尚未在本工程中验证。没有真实接口签名前，不得编造基准面创建或查询 CrownScript。

## 操作图要求

镜像节点必须记录：

- `baseType`；
- `body` 或 `features`；
- 每个输入 ID 的类型和来源；
- `mirrorPlane` 的来源；
- `mergeSolids`；
- 镜像结果的特征 ID 和实体 ID；
- 原实体是否还能继续使用；
- 后续实体操作使用哪个实体 ID。
