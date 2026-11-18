---
name: step-model-acceptance
description: "对照参考 STEP 验收 CrownCAD 当前模型：同步导出当前模型，比较实际几何并记录逐项结果与差异。仅用于明确要求的 STEP 文件间对照，不因提供了 STEP 就自动启用；不负责创建或修改 CAD 模型。"
---

# STEP 模型验收

基于原始参考 STEP、CrownCAD 当前模型的 STEP 导出件和明确的验收要求，逐项判断重建结果。导出成功只证明文件已取得，不证明几何符合要求；单纯统计或渲染相似也不能证明几何等价。

## 必读参考

- 按[验收流程](references/acceptance-workflow.md)执行并记录证据。
- 调用 MCP 工具 `export_step_sync`，取得待验文档的 STEP 文件。
- 读取 [model-geometry-analysis](../model-geometry-analysis/SKILL.md) 和其 [STEP 分析与视图说明](../model-geometry-analysis/references/step-analysis.md)，使用现有 STEP 分析能力，不复制导出或渲染实现。
- STEP 对照通过不能替代模型的原生特征、实际视觉和其他任务必需检查。整体模型交付按[验证流程](../crownscript-executor/references/verification-workflow.md)检查；任务包含装配时另按[装配验收](../crownscript-executor/references/assembly-modeling/assembly-modeling.md#6-装配验收流程)检查。

## 输入和边界

- 确认原始参考 STEP 路径、文件角色、哈希、长度单位、坐标方向，以及本轮 CrownCAD 文档和版本上下文。
- 使用任务已有的必需要求、目标值、单位、容差和容差依据；不得从期望结果反推要求或自行设定验收公差。
- 不执行 CrownScript 建模或修改 CAD 文档。发现模型问题时记录证据和差异，交由建模流程处理。
- 当前导出接口只接收 `documentId`。记录导出前后的 `documentId`、`versionId` 和状态；若导出期间文档状态改变或无法确认导出对应的模型版本，将版本相关结论标为未验证。

## 结论规则

- 每项必需要求标记为“通过”“失败”或“未验证”，附实测值、单位、容差依据和证据引用。
- 任一必需项有确认失败，整体为“验收不通过”。没有确认失败但仍有必需项未验证，整体为“验收未完成”。全部必需项通过且所需视觉、几何及执行证据有效时，整体才为“验收通过”。
- 在当前工具无法测量的项目上明确写“未验证”和缺失原因。不得将 STEP 文件有效、截图相似、统计相同或脚本执行成功单独作为通过结论。
