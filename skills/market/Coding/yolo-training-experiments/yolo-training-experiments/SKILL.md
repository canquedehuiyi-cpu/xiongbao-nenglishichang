---
name: yolo-training-experiments
description: "Plan, run, and compare reproducible Ultralytics YOLO detection training experiments: controlled single-variable sweeps over hyperparameters, augmentation, model size, and epochs; dual best-checkpoint saving by mAP50 and mAP50-95; results.csv comparison; overfitting diagnosis from train/validation curves; and final best-model validation. Use when asked to run multiple YOLO training experiments, save both best.pt and best_mAP50.pt, compare mAP50/mAP50-95/Precision/Recall, judge fitting status, reproduce a training result, or explain identical/ineffective detection augmentations. 触发词：YOLO 批量实验、超参/增强对比、两个 best 权重、mAP50、mAP50-95、过拟合、复现训练、检测结果对比。"
when_to_use: "批量设计、运行、对比 Ultralytics YOLO 检测训练实验，保存 mAP50/mAP50-95 双 best 权重，分析过拟合或复现最佳结果时使用。"
---

# YOLO 检测批量训练实验

## 概述

把 Ultralytics YOLO 检测训练组织成可复现的批量实验：固定基线、单变量对比、同时保存两个 best 权重、用 `results.csv` 横向比较，并在下结论前检查 train/val 拟合状态。

## 何时使用

- 用户要求“排一个训练实验计划”“多跑几组对比”“调学习率/增强/模型大小/epochs”。
- 需要同时保留 `best.pt`（Ultralytics 默认按 mAP50-95 选择）和 `best_mAP50.pt`（按 mAP50 选择）。
- 需要比较 mAP50、mAP50-95、Precision、Recall，判断哪个实验最好。
- 用户问“有没有过拟合”“为什么峰值后下降”“为什么两个实验结果一样”。
- 需要复现某次训练、确认最佳权重位置，或在 val/test/独立图片上验证最佳模型。

不适用：单张图片推理、数据标注、模型导出；这些任务不要触发本 Skill。

## 工作流

### 1. 盘点基线与环境

1. 读取 `data.yaml`，记录 train/val/test 数量、类别数、类别名、imgsz。
2. 找到已有 baseline 的 `results.csv` 和权重，记录 mAP50、mAP50-95、最佳 epoch。
3. 记录环境版本：

```bash
python -c "import torch, ultralytics; print(torch.__version__, torch.cuda.is_available(), ultralytics.__version__)"
```

4. 列出已有 run 名称，后续实验不得覆盖旧版本。需要复跑时，使用新名称或让脚本把旧目录备份为 `*.bak-时间戳`。

### 2. 设计实验矩阵

从 `assets/experiments.example.json` 复制一份配置，至少包含 baseline 和单变量变体：

| 组别 | 变量示例 |
|------|----------|
| 超参 | `lr0`、`optimizer`、`cos_lr`、`weight_decay` |
| 模型 | `yolo12n` / `yolo12s` / `yolo12m` |
| 增强 | `mosaic`、`mixup`、`copy_paste`、HSV、scale、flip |
| 训练量 | `epochs`、数据集版本、`imgsz` |

要求：

- 一次只改一个变量；数据、imgsz、seed、评估方式保持一致。
- 固定 `seed`，run 名称体现变量，例如 `Y12n_lr0005`、`Y12n_copy_paste_05`。
- baseline 必须作为一行参与对比，不能拿历史 run 的峰值直接对比新 run 的 `best.pt`。
- 检测任务不要使用 `erasing`、`auto_augment`；它们只进入分类增强，会被静默忽略。自定义增强使用 `augmentations=[...]`。
- 小数据集不要默认增加模型容量或额外 P2 检测层；先作为假设做单变量实验。

### 3. 启动前预检

```bash
python scripts/run_experiments.py --config experiments.json --dry-run
```

预检会打印每个实验的有效参数，并警告：

- 检测任务中无效的 `erasing` / `auto_augment`；
- 与 baseline 有效参数完全相同的重复实验；
- `save` / `val` 不是 `true` 的配置（脚本会强制开启双 best 所需选项）。

其他检查：

- 确认 `data.yaml` 路径存在、类别数与标签一致。
- Windows 建议 `workers=0`；batch 起点：nano 64、small 32、medium 16，OOM 就降低。
- 明确记录 `conf`、`iou`、`imgsz`，后续对比不得悄悄改变。
- 长训练放后台并保留日志；用 `results.csv` 和 `last.pt` 时间戳确认进度。

### 4. 运行批量实验

```bash
python scripts/run_experiments.py --config experiments.json
```

行为：

- 每个实验使用唯一目录；已存在且未加 `--overwrite` 时拒绝运行。
- `--overwrite` 只把旧目录重命名为 `*.bak-时间戳`，不删除。
- 单个实验失败时记录异常并继续跑后续实验。
- 这是新实验运行器，不要在配置里使用 `resume`；续训请单独处理。
- 结束时输出 `batch_summary.json` / `batch_summary.csv`。

只重跑部分实验：

```bash
python scripts/run_experiments.py --config experiments.json --only Y12n_lr0005,Y12n_copy_paste_05
```

### 5. 同时保存两个 best

Ultralytics 8.4.90 中检测任务的 fitness 等于 mAP50-95（权重 `[0, 0, 0, 1]`），所以默认 `best.pt` 不是 mAP50 最高的 epoch。需要额外保存 `best_mAP50.pt`。

推荐实现：在 `on_model_save` 回调中复制当轮官方 `last.pt`。该回调在 `save_model()` 之后触发，此时 `last.pt` 已是当前 epoch 的标准 checkpoint：

```python
import shutil

def on_model_save(trainer):
    m50 = (trainer.metrics or {}).get("metrics/mAP50(B)")
    if m50 is None:
        return
    if state["best_mAP50"] is None or float(m50) > state["best_mAP50"]:
        state["best_mAP50"] = float(m50)
        state["best_epoch"] = int(trainer.epoch) + 1
        shutil.copyfile(trainer.last, trainer.wdir / "best_mAP50.pt")
```

`scripts/run_experiments.py` 已实现该逻辑，并额外写入 `best_mAP50.json` 记录真实 mAP50、mAP50-95 和 epoch。不要手写 `torch.save({"model": ...})` 自定义 checkpoint；Ultralytics 可能报 `references types outside the supported Ultralytics checkpoint format`。

训练后必须做加载烟雾测试：

```bash
python -c "from ultralytics import YOLO; YOLO(r'results/RUN/weights/best_mAP50.pt')"
```

加载失败时不要继续使用该文件，退回 `best.pt` 并报告失败原因。

### 6. 横向对比结果

```bash
python scripts/analyze_results.py results --markdown comparison.md --json comparison.json
```

报告分两张表，避免把不同 epoch 的指标混在同一行：

1. **按 mAP50 选择**：mAP50 最高 epoch 的 mAP50、同 epoch 的 mAP50-95/P/R、最佳 epoch。
2. **按 mAP50-95 选择**：mAP50-95 最高 epoch 的 mAP50-95、同 epoch 的 mAP50/P/R、最佳 epoch。

同时输出：

- 最后一个 epoch 的指标，以及峰值到最后的下降幅度。
- `best.pt` / `best_mAP50.pt` 是否存在、能否加载。
- 完全相同或近似相同的训练曲线警告。若出现，优先检查参数是否重复、是否用了检测任务无效的增强。

### 7. 判断拟合状态

至少读取以下列：

```text
train/box_loss, train/cls_loss, val/box_loss, val/cls_loss,
metrics/precision(B), metrics/recall(B),
metrics/mAP50(B), metrics/mAP50-95(B)
```

按组合信号判断，不要只看 mAP50：

| 状态 | 典型信号 |
|------|----------|
| 过拟合 | train loss 持续下降，val loss 走平或上升；val mAP 峰值后持续回落；最佳 epoch 之后仍有明显回落（即使峰值出现较晚） |
| 仍在提升 | 最佳 epoch 接近最后一个 epoch；train/val loss 仍在下降；val mAP 仍在上行 |
| 验证噪声 | val mAP 大幅来回波动，峰值与最后差异大但没有一致趋势；小验证集常见 |
| 相对健康 | train/val loss 都下降或稳定，val mAP 稳定或上升，峰值后回落有限 |

规则：

- 报告必须写“拟合状态 + 依据 + 最佳 epoch”，不能只报最高 mAP50。
- 轻度回落不等于严重过拟合；验证集很小时，单轮峰值不可靠。
- 不要因为怀疑过拟合就机械减少 epochs。来源项目中 180 epochs 重训反而低于 200 epochs，可能只是训练方差；把“减少 epochs”作为新实验验证，而不是自动结论。
- 认为过拟合并决定早停时，至少用相同 seed 复跑一次，并保留原最佳权重。

### 8. 复现与最终验证

1. 对最佳配置至少再跑一次同 seed；复现不稳定或提升落在噪声范围内，不宣布新最佳。
2. 有独立 test split 才称“测试集”；没有就明确写“在 val 上评估”。
3. 重新加载权重做最终评估，不要只引用 `results.csv`：

```bash
yolo detect val model=results/RUN/weights/best.pt data=data.yaml split=val imgsz=640 batch=32 device=0
yolo detect val model=results/RUN/weights/best_mAP50.pt data=data.yaml split=val imgsz=640 batch=32 device=0
```

4. 最终评估同时报告整体与每类 P/R/mAP50/mAP50-95、样本量、conf/iou、imgsz。
5. 无标签独立图片可做定性检查：

```bash
yolo detect predict model=results/RUN/weights/best.pt source=IMAGE_TEST/origin conf=0.25 iou=0.45 save=True
```

检测率、类别分布、置信度分布只能作为定性验证，不能当作 mAP。
6. 保留原始 run 和权重，不覆盖旧版本；新结论写入独立报告文件。

## 常见故障

- **`best_mAP50.pt` 无法加载**：自定义 checkpoint 格式错误。改用复制官方 `last.pt` 的方式，并做烟雾测试。
- **两个实验曲线完全一样**：检查是否重复参数，或使用了 `erasing` / `auto_augment` 等检测无效参数。
- **CSV 峰值与 `best.pt` 指标不一致**：两者选择标准不同；确认数值来自 `results.csv` 还是实际权重评估。
- **续训没有 optimizer 状态**：不要直接 `resume=True`；从 `best.pt` 以新 schedule 微调，或先修复 checkpoint。
- **Windows dataloader 卡住**：`workers=0`。
- **OOM**：降低 batch 或模型规模；不要盲目自动重试。
- **升级 Ultralytics 后行为变化**：重新核对回调顺序、fitness 和 checkpoint schema，再做小规模烟雾测试。

## 资源

- `scripts/run_experiments.py`：配置驱动的批量训练；双 best 回调；拒绝覆盖；失败继续；输出汇总。
- `scripts/analyze_results.py`：双指标 best、拟合状态、相同曲线检测、Markdown/JSON 报告。
- `references/ultralytics-pitfalls.md`：已核实的 checkpoint、回调和增强行为。
- `references/mura-case-study.md`：来源项目的已验证结果和教训，仅作单项目先验。
- `assets/experiments.example.json`：实验配置模板。

## 版本基线

行为已在 Ultralytics 8.4.90、RTX 4080 16GB、Windows 环境核实（2026-10）。回调顺序、fitness 或 checkpoint schema 可能随版本变化；升级后先验证再批量运行。
