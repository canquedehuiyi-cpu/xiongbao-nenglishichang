# Ultralytics 行为与失败案例（核实于 8.4.90）

本文件只记录会影响批量实验设计的行为，不替代 Ultralytics 官方文档。升级版本后重新核对。

## 1. `best.pt` 的选优标准

当前检测任务的 fitness 权重是 `[0, 0, 0, 1]`，即：

```text
fitness = mAP50-95
```

因此默认 `best.pt` 是 mAP50-95 最高的 epoch，不保证 mAP50 最高。需要保留 mAP50 峰值权重时，必须额外保存 `best_mAP50.pt`。

## 2. 官方 checkpoint 的保存时序

`Trainer.save_model()` 会：

1. 序列化包含 `ema`、`optimizer`、`train_args`、`train_metrics` 等字段的官方 checkpoint；
2. 写入 `weights/last.pt`；
3. 若当前 fitness 是历史最佳，同时写入 `weights/best.pt`；
4. 返回后触发 `on_model_save`；
5. 随后才触发 `on_fit_epoch_end`。

所以在 `on_model_save` 中复制 `trainer.last` 为 `best_mAP50.pt`，得到的是官方格式，可直接：

```python
from ultralytics import YOLO
YOLO("results/RUN/weights/best_mAP50.pt")
```

复制后请保留一个 sidecar JSON 记录该权重的真实 mAP50、epoch 和伴随指标，因为复制来的 checkpoint 内部 `best_fitness` 仍然是 mAP50-95 的 fitness，不代表 mAP50。

## 3. 不要手写 checkpoint 字典

Ultralytics 加载时会取：

```python
candidate = ckpt.get("ema") or ckpt.get("model")
if not isinstance(candidate, torch.nn.Module):
    raise TypeError(...)
```

来源项目曾保存：

```python
ckpt = {
    "epoch": trainer.epoch,
    "best_fitness": current_m50,
    "model": trainer.ema.ema,
    "ema": trainer.ema.ema.state_dict(),
    "optimizer": None,
    "date": ...,
}
```

加载时报：

```text
TypeError: ERROR ... references types outside the supported Ultralytics checkpoint format
```

不要通过修改 `torch.load` 或关闭安全加载来绕过；直接用“复制官方 last.pt”的方式，或完整复刻当前版本的官方 checkpoint schema。

## 4. 检测任务无效的增强参数

`v8_transforms()`（检测训练）实际包含：

- Mosaic
- CopyPaste
- RandomPerspective
- MixUp
- CutMix
- Albumentations（通过 `augmentations` 传入自定义变换）
- RandomHSV
- RandomFlip

`erasing` 和 `auto_augment` 只出现在 `classify_augmentations()` 中，供分类数据集使用。检测任务不会报错，而是静默忽略它们。典型症状：

- `erasing=0.6` 与默认配置的曲线完全相同；
- `auto_augment=randaugment` 与默认配置的曲线完全相同；
- 实验目录不同，但 `results.csv` 的指标逐 epoch 相同。

排查顺序：

1. 对比两个实验的有效参数；
2. 检查是否使用了上述分类专用参数；
3. 检查是否两份配置只改了 `name`/`desc`；
4. 查看 Ultralytics 版本中 `v8_transforms` 与 `classify_augmentations` 的实际代码。

需要自定义检测增强时，使用 `augmentations=[...]`（Albumentations 变换列表），不要用 `auto_augment`。

## 5. `results.csv` 与权重指标的关系

`results.csv` 是逐 epoch 的验证结果。常见列：

```text
train/box_loss, train/cls_loss, train/dfl_loss,
metrics/precision(B), metrics/recall(B),
metrics/mAP50(B), metrics/mAP50-95(B),
val/box_loss, val/cls_loss, val/dfl_loss
```

对比时注意：

- “mAP50 最高 epoch 的 mAP50-95/P/R”不是“各自的最高值”；
- `best.pt` 按 fitness 选择，CSV 里同一 epoch 的指标可用于核对，但最终评估仍应重新加载权重；
- 不同 run 必须使用同一数据划分、imgsz、conf/iou 和评估代码。

## 6. 拟合判断的实际口径

来源项目中用户明确要求“不要光看 mAP50，看看拟合状态”。有效做法：

1. 在若干代表 epoch（约 1%、20%、40%、60%、80%、最佳 mAP50、最佳 mAP50-95、最后）打印 train/val 的 box/cls loss 和 mAP；
2. 对比最佳点与最后点的 train loss、val loss、mAP；
3. 只有 train loss 持续下降、val loss 走平/上升、val mAP 峰值后持续回落同时出现，才标记较强过拟合信号；
4. 验证集只有几十张时，val 指标会剧烈波动，不能凭单轮峰值判断；
5. 怀疑过拟合而减少 epochs 时，把新 epochs 作为独立实验并复跑，不要直接改原最佳配置。

来源项目中 180 epochs 重训低于 200 epochs，说明“减少 epochs”不一定改善，可能只是训练方差。

## 7. 复现与环境

- 固定 seed 不等于跨设备完全确定；记录 GPU、CUDA、PyTorch、Ultralytics 版本。
- 需要更强确定性时再考虑 `deterministic=True`，并接受速度损失。
- Windows 建议 `workers=0`；多 worker 可能卡住或报进程错误。
- batch 起点按模型规模调整：nano 64、small 32、medium 16（16GB 显存）；OOM 时降低 batch，不要盲目自动重试。
- 升级 Ultralytics 后，先小规模跑 1–2 个 epoch，验证回调、fitness、checkpoint 格式和 CSV 列名。

## 8. 版本核实记录

- 已核对 `ultralytics.__version__ == 8.4.90`。
- 已核对 `DetMetrics.fitness` 权重 `[0, 0, 0, 1]`。
- 已核对 `save_model()` → `on_model_save` → `on_fit_epoch_end` 的调用顺序。
- 已核对 `load_checkpoint()` 对 `ema`/`model` 必须是 `torch.nn.Module` 的要求。
- 已核对 `erasing`/`auto_augment` 只进入分类增强。
