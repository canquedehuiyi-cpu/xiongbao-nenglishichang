# 示例语料库

> 1.0.7 各能力的最小示例与命令行入口（T-1 / G-6 示例库）。
> 全部示例为**本地启发式**检测/建议，输出均标注"估算/非权威"，不承诺通过任何平台检测。

## 一、质量检测（中文）

输入片段：
```
夜色如墨。他攥紧腰间的刀。首先，他回到故乡。其次，他决定查明真相。感到愤怒。
```

命令：
```
python scripts/quality_check.py 示例.md
python scripts/quality_check.py 示例.md --json
```

预期输出要点：
- 语言检测：zh
- 检测项：连接词密度（首先/其次）、情感标签（感到愤怒）、句长CV 等
- 深度维度：句式单一/情绪波动等（`quality_depth.py`）
- 人工质感评分 + TOP3 优先项 + 下一步建议

## 二、人工质感优化（去AI味，中文，三档）

```
python scripts/deai_loop.py 示例.md                # 标准档（默认2轮）
python scripts/deai_loop.py 示例.md --mode 保守    # 保守1轮
python scripts/deai_loop.py 示例.md --mode 深度    # 深度4轮
python scripts/deai_loop.py 示例.md --original 原稿.md   # 对照保留度
```

预期输出：每轮命中规则、人工质感评分前后对比、末尾"改稿后文本（请作者人工复核）"。

## 三、开篇体检（起点口径）

```
python scripts/opening_check.py 开头.md --platform 起点
```

预期输出：前300字冲突/悬念/目标、前3章钩子逐项 pass/fail。

## 四、创作引擎（蒸馏/仿写/续写/润色/对白）

```
python scripts/creation_engine.py distill 样章.md          # 风格档案（8维）
python scripts/creation_engine.py imitate 样章.md "目标文本.md"
python scripts/creation_engine.py continue 样章.md         # 续写方向
python scripts/creation_engine.py polish 样章.md --lock 术语
python scripts/creation_engine.py dialogue 样章.md         # 对白增强
```

预期输出：**供作者人工加工的改稿建议**（非成品正文），含模式档位（conservative/standard/deep）。

## 五、合规引擎（申报清单/体检/改写比例/留痕/标识）

```
python scripts/compliance_engine.py manifest 处理记录.json
python scripts/compliance_engine.py platform 正文.md --platform 晋江
python scripts/compliance_engine.py ratio 原文.md 改稿.md
python scripts/compliance_engine.py trail 原文.md 改稿.md
python scripts/compliance_engine.py label
```

其中 `manifest` 读取**处理记录 JSON**（字段：`modules` 使用模块列表、`text_scope` 覆盖范围、`direct_prose` 是否直出正文）：

```json
{
  "modules": ["去AI味", "润色"],
  "text_scope": "第1-3章",
  "direct_prose": false
}
```

预期输出：AI辅助使用申报清单 / 平台合规风险矩阵（红牌预警越界级别）/ 人工改写比例（参考30%线，明示不替代平台判定）/ 留痕记录（原稿+diff+时间戳）/《标识办法》五条提醒。

## 六、原创自查（洗稿/同质化）

```
python scripts/originality_check.py compare 文本A.md 文本B.md
python scripts/originality_check.py self 正文.md
```

预期输出：2/4/8-gram 重合 + 模板骨架重合 + 同质化指数（低<15/中<25/高≥25），本地自查非权威。

## 七、统一工作流（章节级）

```
python scripts/pipeline.py 全本.md --platform 起点 --chapters
python scripts/pipeline.py 全本.md --json
```

预期输出：安全→质检→叙事→开篇→去味→合规→原创 聚合报告 + 章节级均分/最弱章。

## 八、补充引擎（大纲/标题/编辑视角）

```
python scripts/editor_insight.py outline 大纲.md 正文.md
python scripts/editor_insight.py title "标题" 简介.md
python scripts/editor_insight.py read 正文.md
```

预期输出：大纲要点覆盖情况 / 标题简介钩子检测 / 模拟编辑试读评分与建议。

## 九、多语言（T-2）

输入任意中/英/日/韩文本，质量检测自动识别语言；日韩文本附加语体一致检测（E-7）。报告以输入语言输出。

## 十、长文分块（T-3）

超过约 50000 字的文本建议按章/按 3000-5000 字分段处理；`pipeline.py --chapters` 支持按"第X章"自动拆分并做章节级聚合。

## 十·一、实体状态机与角色/剧情追踪（1.0.7）

```
python scripts/entity_tracking.py 全本.md
python scripts/entity_tracking.py 全本.md --json
python scripts/entity_tracking.py 全本.md --chapter 3
```

预期输出：实体表 + 跨章状态一致性冲突 + 时间轴 + 未回收伏笔 + 章节摘要 + 角色声线档案（本地启发式，非权威）。

## 十·二、情绪曲线量化器（1.0.7）

```
python scripts/emotion_curve.py 章节.md
python scripts/emotion_curve.py 章节.md --json
```

预期输出：段落情绪强度曲线 + 平缓区 + 情绪峰值（爽点）+ 人味情感质量分 + 改写建议。

## 十·三、AI痕迹六层扫描（1.0.7）

```
python scripts/six_layer_scan.py 正文.md
python scripts/six_layer_scan.py 正文.md --profile 用户旧作.md
```

预期输出：词/语/句/语义/指纹/行为六层 0-100 分 + 命中示例 + "主要来源层"结论（提供档案时指纹层改为风格一致性对比）。

## 十·四、红蓝对抗审稿（1.0.7）

```
python scripts/red_blue_review.py 全本.md
python scripts/red_blue_review.py 全本.md --json
```

预期输出：红队挑刺清单（按严重度）+ 蓝队亮点清单 + 裁定结论（聚合实体/情绪/六层结果）。

## 十·五、平台规范实时核实（1.0.7）

```
python scripts/platform_policy_check.py            # 缓存优先
python scripts/platform_policy_check.py --refresh  # 强制联网刷新
python scripts/compliance_engine.py platform 正文.md --platform 起点 --live
```

预期输出：各来源政策要点 + 来源 URL/核实时间（溯源）+ 与内置快照差异告警 + 失败如实标记；`--live` 把实时结果并入合规体检。

## 十一、隐私与本地化（T-4）

所有留痕/台账/反馈数据**仅存本地**，绝不联网上传；仅 `platform_policy_check.py` 联网核实平台政策（失败如实降级）。
