# REF-THR-060 ｜阈值总表（数字定死＋代码闸门 · 单点真源）

> **本册定位**：把全包「能变成数字的规则」收拢成唯一真源。规则写成数字，Agent 写的时候照数锁死；数字交给 `scripts/threshold_scan.py`（第十闸）逐条实测比对，触碰即 FAIL 打回——不靠人眼、不靠感觉、不靠临场判断。

> **执行器**：`scripts/threshold_scan.py`（fail-closed；支持 `--self-test` 阳/阴用例自测）。

> **本册规则**：机读区一行一条阈值，格式 `编号 | 指标 | 比较符 | 数值 | 说明`；指标必须是执行器已实现的 metric，先扩扫描器再入册（新规则落地三问铁则）。

## 一、使用纪律（三条）

1. **改数先改表**：任何一条定数锚（`==`）对应的实际产物数量需要变化时，第一步永远是改本表对应行并走维护备案，再改产物——禁止先改产物后补表（本闸会当场拦住先后颠倒）。
2. **越线即打回**：本闸 FAIL 时按报错行定位：定数锚失守＝数字与真源漂移，回查哪一侧动了；越上限/越下限＝体量或规模失控，回修正引擎收缩后再出包。
3. **能量化的都进表**：新立的规矩凡能用数字界定（条数、字节数、闸数、词数、上限、下限），一律进本表；确实无法量化的才走语言固定，但须有锚点句兜底并经新规则落地三问铁则检验。

## 二、机读区（执行器逐行解析，改行必走备案）

```thresholds
THR-01 | direct_table_entries | == | 46 | 直达表条目定数（真源 REF-DAT-057）
THR-02 | faq_entries | == | 58 | 常见问题条目定数（真源 FAQ.md）
THR-03 | closure_gates | == | 14 | 对话闭环闸数定数（真源 scripts/interaction_closure_scan.py）
THR-04 | visual_rules | == | 9 | 视觉分层规则数定数（真源 scripts/visual_layer_scan.py）
THR-05 | reply_keywords | == | 25 | 回复词定数（SKILL／状态机／直达表三处映射并集，真源 keyword_mapping_scan 同口径）
THR-06 | skill_md_bytes | <= | 120000 | 主文档体量上限（字节；首响读取体量护栏，瘦身常态铁则的量化落点）
THR-07 | ic_range_violations | == | 0 | 正文 IC 全范围引用漂移计数（SKILL＋references 内「IC1–ICN」N∉{6,14} 即违例，「」引用段豁免；扩闸漏同步的机检落点，真源 interaction_closure_scan 实跑闸集）
THR-08 | gate_l3_scanners | == | 13 | 总闸 L3 扫描器数（真源 quality_gate.py 内 L3 区块，机器直读；扩挂新闸先改本行再动代码；非工厂形态包无总闸脚本时本项自动跳过）
THR-09 | growth_base | == | 100361 | 主文档基准字节数＝上一交工版实测（数据行：出包收尾更新为当版实数并走备案；1.0.107 批次4 密度治理后更新）
THR-10 | skill_md_growth | <= | 3200 | 每轮主文档字节增量上限（基准见 THR-09；超限逼新知识下沉分册——时效护栏；3200＝兜底口子与治理痕迹中性化同轮落地一次性归因特批（2026-11-13 拍板「让交付更顺畅」，维护备案在册），2800 前值＝品牌挂载修复＋首响提速功能轮特批，非长期上调，维护备案在册）
THR-11 | skill_md_bytes | <= | 112000 | 主文档收紧上限（较 THR-06 更严一档，双向逼下沉——时效护栏；上调已走维护备案）
THR-12 | references_bytes | <= | 730000 | 分册层字节预算闸（上调已走维护备案；1.0.107 批次4 密度治理备案：低频铁则真源外置金库 R01–R27，主文档同步瘦身约 10KB，分册层增记约 19KB）

```

## 三、指标口径（与执行器逐字对应）

| 指标 | 实测口径 | 类型 | 现值载体 |
| --- | --- | --- | --- |
| direct_table_entries | REF-DAT-057 内 `### DA-` 行计数 | 定数锚 | REF-DAT-057 |
| faq_entries | FAQ.md 内 `**Xn：` 行计数 | 定数锚 | FAQ.md |
| closure_gates | interaction_closure_scan.py 内唯一 IC 编号数 | 定数锚 | scripts/interaction_closure_scan.py |
| visual_rules | visual_layer_scan.py 内唯一 R 编号数 | 定数锚 | scripts/visual_layer_scan.py |
| reply_keywords | 「回复【X】」在 SKILL.md／REF-SM-004／REF-DAT-057 三处并集去重数 | 定数锚 | 三文件映射池 |
| skill_md_bytes | SKILL.md 实际字节数 | 上限型 | SKILL.md |
| ic_range_violations | SKILL.md＋references 内「IC1–ICN」范围引用中 N∉{6,14} 的出现数（6=必备件子集语境，14=现行全闸集真值） | 定数锚 | SKILL.md 与 references 全体 |
| growth_base | 本表 THR-09 行记录的主文档基准字节数（上一交工版实测，出包收尾更新） | 数据行 | 本表 |
| skill_md_growth | 当前 SKILL.md 实际字节数 − 基准（THR-09） | 上限型 | SKILL.md ＋ 本表 |
| gate_l3_scanners | quality_gate.py 内 L3 区块 scripts_dir 条目计数（无总闸脚本的包自动跳过本项） | 定数锚 | scripts/quality_gate.py |
| references_bytes | references/*.md 全部文件字节总和（stat 口径） | 定数锚 | references 目录全体 |

## 四、增补纪律

- 新阈值一律追加机读区新行，编号顺延（THR-07 起），同步补第三节口径行与执行器 metric 函数，缺一即本闸自身报「未知指标」拦下。
- 定数锚数值只随真源侧的有意变更而变，每次变更在维护备案册留痕；禁止为迁就现产物的漂移而回头改表。
- **预算校准权铁则**：THR-06／09／10／11／12 五行调整权只归维护者拍板——越限时执行方只出「预算差额请拍板」报告并停手，禁止自行改表迁就产物；拍板通过后先改本表并备案留痕，再出包。
- 本册随包分发（基准／形态B／master 三线同文），执行器缺失本册即 fail-closed，禁止在无总表的包内裸跑量化判断。

