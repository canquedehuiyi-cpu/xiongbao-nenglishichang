# Ultralytics 实验陷阱与已验证行为

本文件记录已在真实 Mura 检测项目中核实的行为。除特别说明外，环境为 Ultralytics 8.4.90、torch 2.11.0+cu128、Python 3.14、RTX 4080 16GB。升级版本后先做冒烟验证，不要假设行为不变。

## 1. 检测任务的 fitness 只看 mAP50-95

`ultralytics/utils/metrics.py` 中检测框 fitness 的权重是：

```python
w = [0.0, 0.0, 0.0, 1.0]  # [P, R, mAP@0.5, mAP@0.5:0.95]
```

因此默认 `best.pt` 保存的是 **mAP50-95 最高**的 epoch，不一定是 mAP50 最高的 epoch。

真实案例：

| 指标 | 最佳 epoch | mAP50 | mAP50-95 |
|------|-----------|-------|----------|
| 最佳 mAP50 | 152 | 0.8368 | 0.4436 |
| 最佳 mAP50-95 | 112 | 0.7904 | 0.4624 |
| 实际 best.pt | 112 | 0.7909 | 0.4651 |

如果业务更关心 mAP50，必须另存一个 `best_mAP50.pt`，并在报告中说明两个指标的最佳 epoch 可能不同。

## 2. checkpoint 保存顺序

Ultralytics 8.4.90 的 `trainer.save_model()`：

- 每轮把官方 checkpoint 写入 `weights/last.pt`；
- 当前 fitness 等于历史最佳时，同一份字节写入 `weights/best.pt`；
- 保存成功后触发 `on_model_save`；
- 之后才触发 `on_fit_epoch_end`。

因此双 best 回调应挂 `on_model_save`，在此时复制 `last.pt`。复制出来的是官方格式，`YOLO(path)` 可直接加载。`on_fit_epoch_end` 也能用，但 `on_model_save` 的时序更明确。该事件依赖 `save=True` 且本轮成功写盘；回调还需要 `val=True` 产生的 mAP50。缺少任一条件时不会生成 `best_mAP50.pt`。

## 3. 自定义 checkpoint 会加载失败

会话中曾用如下思路保存 `best_mAP50.pt`：自己构造 `torch.save` 字典，把 `trainer.ema.ema` 等对象直接放进去。结果：

- `YOLO("best_mAP50.pt")` 报 `TypeError: references types outside the supported Ultralytics checkpoint format`；
- `torch.load(...)` 报 `_pickle.UnpicklingError: Weights only load failed`，涉及 `numpy._core.multiarray.scalar`。

结论：不要自造 checkpoint schema。正确方式是复制官方 `last.pt`，把 mAP50、epoch、mAP50-95 写到 sidecar JSON。

## 4. erasing 与 auto_augment 对检测无效

`erasing` 和 `auto_augment` 主要服务分类管线。检测实验中开启后结果与基线完全相同（相同 seed、相同训练配置）。检测任务优先使用：

- `mosaic`
- `mixup`
- `copy_paste`
- `hsv_h/hsv_s/hsv_v`
- `degrees/translate/scale/shear/perspective`
- `flipud/fliplr`

真实项目中 `copy_paste` 的提升也有限（<1%），不要把它当成稳定的大幅增益。

## 5. 迁移/中断 checkpoint 可能丢状态

从其他主机复制或中断的训练目录中，`last.pt` 可能出现：

- `epoch == -1`
- `best_fitness is None`
- 缺少 optimizer/scaler 状态

直接 `resume=True` 可能从头开始、跳过验证或无法恢复学习率。处理顺序：

1. 先检查 `epoch`、`best_fitness`、`optimizer` 键；
2. 必要时修复 checkpoint 元数据；
3. 状态不完整时，从 `best.pt` 以新 schedule 微调，而不是假装续训。

注意区分“损坏”和“已 strip”：

- 最终发布用的 `best.pt` 经过 `strip_optimizer` 后，`epoch=-1`、`best_fitness=None`、`optimizer/ema/updates/scaler=None` 都是正常的；
- 这种权重用于推理/验证，不要用来续训；
- 真正要检查的是训练目录里的 `last.pt`：如果它缺 optimizer/ema 或 `epoch=-1`，才说明续训状态不完整。

### 5.1 早停会让实际 epoch 小于配置值

`results.csv` 的最后一个 `epoch` 是实际完成轮数。配置 `epochs=500`、`patience=60` 时，最佳 epoch 382 之后最多再跑 60 轮，实际可能在 442 轮结束。报告应写“实际 442 轮，最佳 382”，不要写“500 轮全部完成”。

## 6. 小数据集上的容量选择

真实 Mura 数据集约 948 张 train / 94 张 val：

- YOLO12s/m 比 YOLO12n 更差；
- 增加 P2 检测层（4 个尺度）更差；
- 200 epochs 最佳点常在中后段，500 epochs 最佳点也可能在 382 左右；
- 最佳模型之后通常只出现轻微回落，但 val loss 会先上升。

不要因为“模型更大/层更多”就默认更好。先跑 baseline 和单变量对照。

## 7. `model.val` 的分类别 API

`metrics.box.class_result(i)` 返回 `(precision, recall, ap50, ap)`。不要写：

```python
metrics.box.precision[i]  # AttributeError
```

真实报错：`'Metric' object has no attribute 'precision'`。

整体指标用：

```python
metrics.box.map50
metrics.box.map
metrics.box.mp
metrics.box.mr
```

## 8. 无标签独立验证

- 100 张抽样适合快速检查；500 张更稳定。真实项目中 100 张检测率 23%，500 张（499 张有效）检测率 24.2%，量级一致。
- 必须固定 seed，记录 conf/iou。真实项目使用 `conf=0.25`、`iou=0.45`。
- 必须逐张捕获异常：遇到损坏图片时 `results` 可能为空，直接 `results[0]` 会 `IndexError`；应跳过并在报告中计数。
- 检测率低可能是“多数图片正常”，也可能是漏检；必须人工抽查可视化，不能把无标签结果当成 mAP。
- 没有独立 test split 时，只能称“在 val 上评估”。

## 9. 推理阈值

Ultralytics 默认：

- `predict`: `conf=0.25`, `iou=0.7`
- `val`: `conf=0.001`, `iou=0.7`

Mura 缺陷通常不密集，真实项目在独立验证中使用 `iou=0.45`。推理参数与验证参数不是一回事：`val` 的 `iou` 是评估时的 NMS 阈值；训练参数里的 `iou` 是损失相关阈值，不要混用。

## 10. 可复现性

同一配置、同一 seed 仍可能有小幅波动：

- 200 epochs 原结果 0.9162，复现 0.9150（差 0.13%）；
- 500 epochs 一次 0.9713，复现 0.9774（更好）；
- 400 epochs 为 0.9627。

比较实验时给复现差异留出容忍度，不要用 0.1% 的差异下强结论；同时报告 mAP50 与 mAP50-95。

## 11. 升级后的检查清单

1. 打印 `ultralytics.__version__`。
2. 确认 `trainer.save_model` 仍然先写 `last.pt`，再触发 `on_model_save`。
3. 确认检测 fitness 仍以 mAP50-95 为主。
4. 用 1–2 epochs 冒烟训练，验证 `best_mAP50.pt` 能被 `YOLO()` 加载。
5. 用 `analyze_results.py` 对旧 `results.csv` 跑一遍，确认列名未变。
6. 用 `validate_model.py --mode labeled` 验证分项指标 API 未变。
