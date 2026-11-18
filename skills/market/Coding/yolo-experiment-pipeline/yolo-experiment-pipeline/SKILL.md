---
name: yolo-experiment-pipeline
description: "Design, run, and analyze reproducible Ultralytics YOLO detection experiments: controlled comparison plans, dual best-checkpoint saving by mAP50 and mAP50-95, overfitting diagnosis from results.csv, and best-model validation on labeled or independent images. Use when comparing YOLO models/hyperparameters/augmentation, resuming or reproducing training, saving best weights by a chosen metric, judging fitting status, or validating a detector. 触发词：YOLO 对比实验、调参、增广、mAP50、mAP50-95、best.pt、过拟合、复现训练、独立验证。"
---

# YOLO 对比实验流程

## 概述

把 Ultralytics YOLO 检测实验做成可复现、可比较、可验证的流水线：固定基线并单变量对比；训练时同时保留 mAP50 与 mAP50-95 两个 best 权重；用 `results.csv` 判断拟合状态；最后在 val/test 或独立图片上验证最佳权重。

## 何时使用

- 对比 YOLO 模型、学习率、优化器、epochs、模型规模或数据增广。
- 发现 `best.pt` 指标低于 CSV 峰值，或需要同时保存两个指标的最佳权重。
- 判断训练是否过拟合、是否需要早停、最佳 epoch 在哪。
- 复现实验、续训或迁移 checkpoint。
- 用最佳模型在 val/test 或独立图片上评估。

## 工作流

以下命令中的 `$SKILL_DIR` 指本 Skill 根目录（包含 SKILL.md 的目录）。

### 1. 环境与基线核查

先记录数据与基线，再开始新实验：

- 读取 `data.yaml`，记录 train/val/test 数量、类别数、类别名、imgsz。
- 找到已有 baseline 的 `results.csv` 与权重，记录 mAP50、mAP50-95、最佳 epoch。
- 确认环境；已经能正常训练时不要重装 PyTorch：

```bash
python -c "import torch, ultralytics; print(torch.__version__, torch.cuda.is_available(), ultralytics.__version__)"
```

- 迁移或中断的 checkpoint 先检查再续训（仅加载可信文件）：

```python
import torch
ckpt = torch.load("last.pt", map_location="cpu", weights_only=False)
print(ckpt.get("epoch"), ckpt.get("best_fitness"), "optimizer" in ckpt)
```

若 `epoch == -1`、`best_fitness is None` 或没有 optimizer 状态，不要直接 `resume=True`；修复 checkpoint，或从 `best.pt` 以新 schedule 微调。注意：最终发布用的 `best.pt` 经 `strip_optimizer` 后本来就会是 `epoch=-1`、`best_fitness=None`、无 optimizer，这是正常格式，只用于推理/验证，不能续训。

### 2. 实验设计

一次只改一个变量，其他条件（数据、imgsz、seed、评估方式）保持一致：

| 组别 | 变量 | 示例 |
|------|------|------|
| A 超参 | `lr0`、optimizer、`cos_lr` | `lr0=0.001 → 0.005` |
| B 模型 | nano/small/medium | `yolo12n → yolo12s` |
| C 增广 | mosaic、mixup、copy_paste | `copy_paste=0.5` |
| D 训练量 | epochs、数据集 | `200 → 400 → 500` |

要求：

- 固定 `seed=42`，run 名称体现变量，例如 `Y12n_lr0005`、`Y12n_copy_paste`。
- 记录完整训练参数（`args.yaml` 会保存在 run 目录）。
- 比较时使用同一指标来源；不要拿 A 的 CSV 峰值对比 B 的 `best.pt`。
- 小数据集默认避开已知低收益方向：更大的模型、额外 P2 检测层、检测任务里的 erasing/auto_augment。

### 3. 训练与监控

RTX 4080 16GB 的起点配置（nano/640）：

```python
model.train(
    data="data.yaml",
    epochs=200,
    imgsz=640,
    batch=64,
    device=0,
    workers=0,
    optimizer="SGD",
    lr0=0.005,
    lrf=0.01,
    weight_decay=0.003,
    warmup_epochs=15,
    patience=60,
    seed=42,
    close_mosaic=10,
    amp=True,
    mosaic=1.0,
    project="results",
    name="Y12n_lr0005",
    exist_ok=True,
)
```

- batch 起点：nano 64、small 32、medium 16；OOM 就降低，不要盲目自动重试。
- Windows 使用 `workers=0`，避免 dataloader 进程问题。
- 长训练放后台并保留日志；用 `results.csv`、`last.pt` 时间戳、GPU 占用确认进度。
- 训练中不要改其他变量；需要变更就新建 run。

### 4. 双 best checkpoint

Ultralytics 检测任务的 fitness 只等于 mAP50-95，因此默认 `best.pt` 可能不是 mAP50 最高的 epoch。

正确做法：在 `on_model_save` 回调里复制当轮官方 `last.pt`，不要自己拼 checkpoint 字典：

```python
from ultralytics import YOLO
import sys
sys.path.insert(0, r"/path/to/yolo-experiment-pipeline/scripts")  # 替换为实际 Skill scripts 目录
from dual_best_checkpoint import attach_dual_best_checkpoint

model = YOLO("yolo12n.pt")
attach_dual_best_checkpoint(model)  # 生成 weights/best_mAP50.pt + best_mAP50.json
model.train(...)
```

原理：`save_model()` 每轮先写 `last.pt`，随后触发 `on_model_save`；复制出来的是官方格式，`YOLO()` 能直接加载。`best_mAP50.json` 记录该权重的真实 mAP50、mAP50-95 和 epoch。保持默认 `save=True`、`val=True`，否则回调拿不到指标或不会被触发。

续训前先备份或移走现有的 `best_mAP50.pt` 与 `best_mAP50.json`；回调在新进程里从 `-inf` 重新计数，否则可能用较低 mAP50 覆盖旧文件。

训练后必须验证：

```bash
python "$SKILL_DIR/scripts/dual_best_checkpoint.py" --verify results/RUN/weights/best_mAP50.pt
python "$SKILL_DIR/scripts/validate_model.py" --model results/RUN/weights/best_mAP50.pt --mode labeled --data data.yaml --split val
```

禁止把自定义 `torch.save({"model": ...})` 文件当作 Ultralytics 权重；这种文件可能报 `references types outside the supported Ultralytics checkpoint format` 或 `_pickle.UnpicklingError`。

### 5. 结果与过拟合诊断

用脚本汇总所有 run：

```bash
python "$SKILL_DIR/scripts/analyze_results.py" results/RunA results/RunB --markdown comparison.md --json comparison.json
```

报告必须同时包含：

- mAP50 最佳 epoch 与数值、mAP50-95 最佳 epoch 与数值、最后 epoch 数值。
- 最佳到最后的 mAP50 / mAP50-95 下降百分比。
- train/box_loss 与 val/box_loss 在最佳点和最后点的变化。
- 最佳 epoch 在总 epochs 中的位置。
- `results.csv` 的 `epochs` 是实际完成轮数，早停会小于配置值；不要把 442 轮误读成没有训练完。
- 两个指标的最佳 epoch 是否不同；默认 `best.pt` 对应 mAP50-95。

判断过拟合时看组合信号，不要只看峰值：

- train loss 继续下降，同时 val loss 上升；
- val mAP 在峰值后持续回落；
- 最佳 epoch 明显早于训练结束；
- val 指标剧烈波动（小验证集常见）。

轻度回落不等于严重过拟合。报告要写“拟合状态 + 依据”，不要只写“最高 mAP50”。

### 6. 最佳模型验证

先确认是否存在独立 test split。没有就明确写“在 val 上评估”，不要称为测试集。

有标签数据：

```bash
python "$SKILL_DIR/scripts/validate_model.py" \
  --model results/RUN/weights/best.pt \
  --mode labeled \
  --data data.yaml \
  --split val \
  --imgsz 640 \
  --batch 32 \
  --device 0 \
  --output validation.json \
  --markdown validation.md
```

输出整体与每类 P/R/mAP50/mAP50-95、推理速度。需要对比两个权重时分别运行。

无标签独立图片：

```bash
python "$SKILL_DIR/scripts/validate_model.py" \
  --model results/RUN/weights/best.pt \
  --mode images \
  --source IMAGE_TEST/origin \
  --sample 500 \
  --seed 42 \
  --conf 0.25 \
  --iou 0.45 \
  --save-visuals \
  --output-dir IMAGE_TEST/validation_results
```

规则：

- 先 100 张快速检查，再 500 张提高稳定性。
- 固定 seed，记录 conf/iou；损坏图片必须跳过并计数，不能让整批中断。
- 输出检测率、类别分布、置信度分布、按文件夹统计和可视化目录。
- 无标签推理是定性验证，不是 mAP；不能仅凭低检测率或高置信度宣称可生产。

### 7. 报告模板

```markdown
| Run | mAP50 | best ep | mAP50-95 | best ep | last mAP50 | 峰值后下降 | val loss 变化 | 拟合状态 |
|-----|-------|---------|----------|---------|------------|------------|---------------|----------|
| ... | ...   | ...     | ...      | ...     | ...        | ...        | ...           | ...      |

最佳权重：
- best.pt（mAP50-95）：<path>，指标 <...>
- best_mAP50.pt（mAP50）：<path>，指标 <...>

验证：
- 数据：val/test/独立图片；样本量 ...
- 指标：...
- 限制与风险：...
```

## 关键规则与陷阱

- **fitness 只用 mAP50-95**：Ultralytics 8.4.90 的检测 fitness 权重为 `[0, 0, 0, 1]`；`best.pt` 默认不是 mAP50 最高。
- **CSV 峰值 ≠ 保存权重**：对比前先确认数值来自 `results.csv` 还是实际 `best.pt` 的 `val`。
- **自定义 checkpoint 风险**：不要保存含 EMA 模块/自定义对象的字典；复制官方 `last.pt` 最稳。
- **erasing/auto_augment 对检测无效**：它们走分类管线；检测优先 mosaic、mixup、copy_paste、HSV、scale、flip。
- **小数据集不要盲目加容量**：更大模型、额外 P2 层在小训练集（如 948 张）上可能更差。
- **小 val 集波动大**：94 张 val 的单轮峰值不可靠；看趋势、窗口均值和多个信号。
- **迁移/中断的 `last.pt` 可能丢状态**：`epoch=-1`/`best_fitness=None` 时先修复或改微调。
- **不要自动删除/移动数据**：数据清理必须单独确认，实验流程只负责训练、评估和分析。
- **版本差异**：回调顺序、fitness、checkpoint schema 可能随 Ultralytics 版本变化；升级后重新验证。

## 资源

- `scripts/dual_best_checkpoint.py`：双 best 回调；复制官方 `last.pt`，写 sidecar JSON，支持自检与权重加载验证。
- `scripts/analyze_results.py`：读取一个或多个 `results.csv`，输出两个指标的最佳 epoch、峰值后下降、loss 变化、拟合评估和对比表。
- `scripts/validate_model.py`：有标签 `val` 评估或无标签图片抽样推理；跳过损坏图片，输出 JSON/Markdown。
- `references/ultralytics-pitfalls.md`：已核实的 Ultralytics 行为、失败案例和版本注意事项。

## 版本基线

行为已在 Ultralytics 8.4.90、torch 2.11.0+cu128、Python 3.14、RTX 4080 16GB 上核实（2026-10）。其他版本先做小规模冒烟验证。
