# 物料齐套核对 · 调用参考

> 精确调用式与任务契约。运行目录：本技能目录（SKILL.md 所在目录）。

## 引擎入口

```bash
python <本技能目录>/engine/main.py tasks --scenario material_kitting_check --json
python <本技能目录>/engine/main.py run --scenario material_kitting_check --json --task check-kitting <输入文件>
```

- 依赖：Python 3.10+；第三方依赖见 `<本技能目录>/build/requirements.txt`。
- 运行根：引擎在 `<本技能目录>/dist_template/` 自动创建（产物 output/、状态 storage/）。
- 退出码：0=完成（含待复核）、1=输入失败、2=场景未绑定。

## 输入格式

行格式、键名别名、判定与转人工规则见
[INPUT_CONTRACT.md](../../scenarios/material_kitting_check/INPUT_CONTRACT.md)。

## 红线

- 只输出定位/存在性/一致性事实，不输出选商、下单、放行、废标等业务结论。
- 未匹配/不可比/未解析项原样转人工，不自动消掉。
