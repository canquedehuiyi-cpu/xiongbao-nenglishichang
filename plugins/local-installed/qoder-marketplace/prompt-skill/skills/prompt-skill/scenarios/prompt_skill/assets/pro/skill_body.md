# Prompt 修复与 Skill 质检产线

把「Prompt 修复 / 按描述新建 / 质量认证 / 封装 Skill / 技能质检 / 打包交付」收敛为
六个**互相独立**的确定性任务。引擎零模型调用：评分、装配、断言、指纹全部写死在
本地 Python 引擎内；**Prompt 的语义改写与被测技能的执行回填，全部由宿主 Agent（你）完成**
——评分结论只认引擎报告，严禁你自评替代。

## 何时使用

用户拿来粗糙 Prompt 要修/要评级；或只有一句话描述要产出标准 Prompt；或要把达标的
Prompt 产品化成可挂载 WorkBuddy/Trae 的 Skill 目录并交付。

## 使用方法（产线 SOP，按序执行）

| 顺序 | 任务 | 输入 | 产出 |
|---|---|---|---|
| 1a | `fix-prompt` | 旧 Prompt 文件 | 诊断报告 + 逐条修复清单 |
| 1b | *(你)* | 按清单**一次性**改写 | 修复稿文件 |
| 2 | `draft-prompt` | 任务描述一句话 | 标准骨架（含【待填】槽）→ *你补槽* |
| 3 | `score-prompt` | 修复稿 / 填好的骨架 | **体系A 认证**：达标=可用。同一文本第二次仍不达标会被闸门强制转人工 |
| 4 | `build-skill` | 达标 Prompt + 技能名 + 权限档位 | ``dist_template/output` 下的 `skills`/〈name〉/` AWP 目录（SKILL.md+PERMISSIONS+5 个种子用例） |
| 5 | *(你)* | 逐条执行包内 `testcases/*.json` 的 `input`，把技能**原样响应**存为 ``dist_template/storage` 下的 `responses`/〈case_id〉.txt` | 响应矩阵 |
| 6 | `score-skill` | 该目录的 `SKILL.md` | **体系B 认证**：结构+断言+通过率。响应目录缺失时自动降级为结构自检（DEGRADED，不算可用） |
| 7 | `ship-skill` | 同上 | 认证指纹一致才出 zip+manifest；未认证/认证后改动一律拒绝 |

CLI 示例（`--json` 契约见下节；skill-file 类任务用 `--set`）：

```
python engine/main.py run --scenario prompt_skill --json --task fix-prompt 旧Prompt.md
python engine/main.py run --scenario prompt_skill --json --task build-skill 旧Prompt.md --set skill-name=my-skill --set net-policy=无网络·只读工作区
python engine/main.py run --scenario prompt_skill --json --task score-skill --set skill-file=技能目录/SKILL.md
```


## 不要做什么

- **不要替引擎下结论**：达标与否只以 `dist_template/output/*-cert-*.md` 报告与 JSON `state` 为准；
  报告说「未达标」就必须如实告知，不得美化
- **不要凑词刷分**：体系A 查的是契约实质；为命中词表硬塞关键词会卡在你没写的
  adversarial 用例与人工审查上
- **不要改断言凑通过**：`testcases/*.json` 的 `asserts` 只支持
  `nonempty / contains: / not-contains: / regex:` 四种机器形式；种子断言全是
  `nonempty` 占位，**体系B 的 B5 硬闸会判它"空转未测"直接不达标**——交付前必须
  按技能说明书把每个用例升级成具体预期（`contains:` 关键字段 / `regex:` 结构）。
  升级会改包指纹，认证后任何改动都要重跑 `score-skill`
- **不要绕过 ship 闸门**：手工压 zip 交付 = 放弃质量背书；闸门拒绝时把原因转告用户，
  引导走认证/人审，而不是自行打包
