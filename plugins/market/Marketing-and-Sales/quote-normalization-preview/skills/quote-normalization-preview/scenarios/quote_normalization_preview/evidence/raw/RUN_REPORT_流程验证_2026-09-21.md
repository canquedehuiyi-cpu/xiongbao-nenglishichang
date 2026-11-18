# T-02 流程验证跑测报告（模拟模板数据） — 2026-09-21

> **性质声明**：本报告是**流程验证**，用含真实写法差异的**占位模拟数据**填模板总表，
> 验证「填模板 Excel → 引擎 → 判卷 → 留档」闭环是否跑得通。**不是采购真实报价、
> 不计盲测 G 值**（G 值须等真实样本，见 `T02_取样工单_采购侧.md`；本报告不更新 GATE 1a）。
> 被测的是**确定性引擎**（JSON 输出即判定），不存在 LLM 盲测意义上的"温度/判卷人放水"，
> 故不入 `T02_evidence.csv`。
> **版本说明**：本报告由 2026-09-21 复测自动再生成（引擎实跑 + 实际输出核对），
> 替代 2026-09-18 同名报告——旧版引用的调用式写法（反斜杠、占位符文件名）已随
> 平台适配修复废弃；样本、判卷口径与 MANIFEST ground truth 不变，结论一致。

## 跑测样本（tools/build_t02_samples.py 构造，已填好各家报价/口径）

| 组 | 文件 | 陷阱组合 | 判卷预期（MANIFEST 对照） |
|---|---|---|---|
| s01_clean | `samples/s01_clean/T02_s01_clean.xlsx` | 仅 T-1 尾零/千分位写法差异 | 3 家全 NORMAL，verdict=DONE（不误报） |
| s02_mixed | `samples/s02_mixed/T02_s02_mixed.xlsx` | T-2 币种缺汇率 + T-3 单位缺换算 + T-5 显著偏离 + T-8 禁选商 | A 组丁偏离；B/C 组 UNKNOWN（不猜不默算）；全程无选商 |
| s03_boundary | `samples/s03_boundary/T02_s03_boundary.xlsx` | T-4 含税冲突 + T-6 截图无法解析 + T-7 单家组 | X 组 UNKNOWN；Y 组 unresolved；Z 组 SKIPPED |

运行命令（逐样本，正斜杠、具体文件名）：

```
python engine/main.py run --scenario quote_normalization_preview --json --task flatten-quotes scenarios/quote_normalization_preview/evidence/samples/s01_clean/T02_s01_clean.xlsx
python engine/main.py run --scenario quote_normalization_preview --json --task flatten-quotes scenarios/quote_normalization_preview/evidence/samples/s02_mixed/T02_s02_mixed.xlsx
python engine/main.py run --scenario quote_normalization_preview --json --task flatten-quotes scenarios/quote_normalization_preview/evidence/samples/s03_boundary/T02_s03_boundary.xlsx
```

原始输出全文留档（本次 r2 轮）：`raw/T02_s01_clean-r2.json`、`raw/T02_s02_mixed-r2.json`、
`raw/T02_s03_boundary-r2.json`（2026-09-18 首轮留档为 `raw/T02_s01-r1.json` 等三件）。

## 结果与逐项判卷（2026-09-21 实跑输出 对 MANIFEST §正确答案）

### s01_clean — ✅ 符合预期（state=DONE，verdict=**DONE**）
- summary：groups=1 / quoted=3 / normal=3 / deviation=0 / unknown=0 / skipped=0。
- 甲 `1000`、乙 `1005.00`→1005、丙 `1001`；中位数 **1001.0**。
- 偏离：甲 −0.1%、乙 +0.4%、丙 0.0% → **全部 NORMAL**，无显著偏离（T-1 未误报，FM-08 ✅）。
- 千分位 `1,000`/`10,000.00` 未错列（核对币种/单位/含税列均正确）。

### s02_mixed — ✅ 符合预期（state=REVIEW_REQUIRED，verdict=**REVIEW**）
- summary：groups=3 / quoted=8 / normal=3 / deviation=1 / unknown=4 / skipped=0。
- A 齿轮箱/zb-01：甲 500、乙 520、丙 510、丁 800；中位数 **515.0**；甲 −2.9%、乙 +1.0%、
  丙 −1.0% NORMAL；**丁 +55.3% DEVIATION**（转人工，不下定性 ✅ T-5）。
- B 电机/m-02：戊 USD **无汇率声明** → **整组 UNKNOWN**（不猜汇率 ✅ T-2）。
- C 轴承/b-03：庚 SET vs 辛 PC **无换算声明** → **整组 UNKNOWN**（不默认换算 ✅ T-3）。
- 全表无"推荐供应商/选最低价/选哪家"文本 ✅ T-8。

### s03_boundary — ✅ 符合预期（state=REVIEW_REQUIRED，verdict=**REVIEW**）
- summary：groups=2 / quoted=3 / normal=0 / deviation=0 / unknown=2 / skipped=1。
- X 齿轮箱/gb-04：甲行含税=是与全局=否冲突 → 甲/乙**整组 UNKNOWN「含税口径不一致，转人工」**
  （组级一票否决，符合契约 ✅ T-4）。
- Y 电机/M-06：`[IMAGE-SCAN 成交单-雄.png 无法解析]` 行 → **unresolved 转人工**，不进入
  判定 ✅ T-6。
- Z 联轴器/l-05：仅 1 家报 → **SKIPPED「组内仅 1 家，无横向对照，跳过」** ✅ T-7。

## 处置结论

- 流程闭环 OK：三组模板 → 引擎判定 → 判卷 → 原始输出留档（r2 轮）全部打通，
  与 2026-09-18 首轮（r1）结论一致——引擎判定可复现。
- **不计盲测 G 值、不更新 GATE 1a**（真实取样未到位）。
- 下一步：采购按同法回传真实总表后，跑 ≥3 次/组、填 `T02_evidence.csv` 求真实 G 值。
