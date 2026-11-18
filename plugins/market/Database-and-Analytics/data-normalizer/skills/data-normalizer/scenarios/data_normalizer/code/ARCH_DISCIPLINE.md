# 数据标准化 包 —— 架构纪律（内建于脚手架，落地即生效）

> 本文件由 `tools/new_scenario.py` 生成时即写入。**约束随包诞生，不是事后靠测试消防。**

## 1. import 边界（ARCH-B-002，单一事实来源 `tests/architecture/arch_guard.py`）

本包 `.py` 只允许：
- **相对导入**（同包内跨模块）；
- 顶层 import `scenario_api` / `yaml` / **标准库**。

禁止：`openpyxl`、`pandas`、`requests`、其他第三方库的直接 import。
需要读文件/Excel/读文本、注册读器**全部经 `scenario_api` 能力**（如
`read_file_auto`、`read_excel_rows`、`read_text_auto`），引擎能力只经
`ctx.runtime` 白名单触达。包内不 import `engine` 任意模块。

## 2. 生成即校验

`new_scenario.py` 建包那一刻已对该包全 `code/*.py` 跑过 arch_guard 白名单扫描，
违规会**当场抛错**而非留到测试。此后任何改动，都必须再跑：

```
python -m pytest tests\architecture/test_boundaries.py -q
```

复跑未过 → 先回改 import，再谈功能。

## 3. 解析他人数据 → 先用输入攻击面清单

本包若解析外部/第三方数据（Excel/CSV/PDF/DOCX/报价……），写码前先按
`code/parser_attack_surface.md`（由 `tools/INPUT_ATTACK_SURFACE.md` 拷入）把
"会破坏列/行/字段对齐的输入"逐条过一遍；每个适用项配一条破坏性输入测试。

## 4. 硬规则速记

- 只做文本层处理，零 LLM 调用；截图/扫描必须先转文字，否则拒绝转人工。
- 数值一律代码算；缺声明不换算；原始值永远保留不覆盖。
- 不改 `scenario_api` / 不改 route 边界；能力不足回退到把手动作，不硬造。
- 新增 import 前先自问：它进得了 `scenario_api`/`yaml`/标准库吗？进不了就别用。