"""
steps.py —— 发文前核对·适配层

**这一层不做判定。** 步骤只干三件事:
1. 从 ctx.inputs 拿输入(推文全文 + 可选参数白名单 + 本地个人词典);
2. 调判定能力(本包 checker.check_text 纯函数)拿结构化事实;
3. 把事实翻译成引擎的语言(ctx.outputs / ctx.issues)。

check 任务管线:step_parse_validate → step_judge → step_render。
dict 任务管线:step_dict_parse → step_dict_exec → step_render(词典只影响白名单,不碰判定)。

本地词典(NON_GOALS:零上云):~/.gzh-typo-check/dictionary.txt 一行一词;
加载失败降级为 WARN + 只用参数白名单,不炸主流程(02_USER_FLOW 异常路径)。
"""

from __future__ import annotations

from scenario_api import Issue, IssueLevel, RunContext

from . import checker, dict_store


def step_parse_validate(ctx: RunContext) -> None:
    """归一 + 校验输入:空文本记 ERROR;超长记 ERROR(异常路径:提示分段核对)。"""
    raw = str(ctx.inputs.get("text", "") or "")
    ctx.outputs["source_chars"] = len(raw)
    if not raw.strip():
        ctx.issues.append(
            Issue(IssueLevel.ERROR, "输入是空的:未收到推文文本,没有可核对的内容")
        )
        return
    if len(raw) > checker.MAX_CHARS:
        ctx.issues.append(
            Issue(
                IssueLevel.ERROR,
                f"文本超长:{len(raw)} 字,超过上限 {checker.MAX_CHARS} 字;请分段核对",
            )
        )
        return
    ctx.outputs["text"] = raw


def _effective_whitelist(ctx: RunContext) -> tuple[str, ...]:
    """参数白名单 + 本地词典合并;词典加载失败降级(WARN),不炸。"""
    raw = str(ctx.inputs.get("whitelist", "") or "")
    param_words = tuple(w for w in (s.strip() for s in raw.split(",")) if w)
    try:
        dict_words = dict_store.load_words()
    except dict_store.DictStoreError as exc:
        ctx.issues.append(Issue(IssueLevel.WARN, f"{exc};本次只用参数白名单"))
        dict_words = ()
    merged: dict[str, None] = {}
    for w in (*param_words, *dict_words):
        merged[w] = None  # dict 保序去重
    return tuple(merged)


def step_judge(ctx: RunContext) -> None:
    """判定:调 checker 纯函数,把命中清单翻译成报告输出。判定不住在这里。"""
    text = ctx.outputs.get("text")
    if text is None:  # 归一步已记 ERROR,这里不再臆造结论
        ctx.outputs["verdict"] = "NOT_RUN"
        return
    report = checker.check_text(text, _effective_whitelist(ctx))
    ctx.outputs["verdict"] = report.verdict
    ctx.outputs["report"] = {
        "hard": [h.to_row() for h in report.hard],
        "hard_count": len(report.hard),
        "uncovered": list(report.uncovered),
    }


# ---------------------------------------------------------------- dict 任务
def step_dict_parse(ctx: RunContext) -> None:
    """归一 dict 任务输入:action(add/list/remove)与词表。"""
    action = str(ctx.inputs.get("action", "") or "").strip().lower()
    if action not in ("add", "list", "remove"):
        ctx.issues.append(
            Issue(IssueLevel.ERROR, f"action 必须是 add/list/remove,收到「{action}」")
        )
        return
    ctx.outputs["action"] = action
    raw = str(ctx.inputs.get("words", "") or "")
    ctx.outputs["words"] = tuple(w for w in (s.strip() for s in raw.split(",")) if w)


def step_dict_exec(ctx: RunContext) -> None:
    """执行词典操作。词典只影响白名单,不碰判定规则。"""
    action = ctx.outputs.get("action")
    if action is None:  # 归一步已记 ERROR
        ctx.outputs["dict_result"] = {"ok": False}
        return
    words: tuple[str, ...] = ctx.outputs.get("words", ())
    try:
        if action == "add":
            added = dict_store.add_words(words)
            ctx.outputs["dict_result"] = {"ok": True, "action": "add",
                                          "added": added, "words": list(words)}
        elif action == "remove":
            removed = dict_store.remove_words(words)
            ctx.outputs["dict_result"] = {"ok": True, "action": "remove",
                                          "removed": removed}
        else:  # list
            current = dict_store.load_words()
            ctx.outputs["dict_result"] = {"ok": True, "action": "list",
                                          "count": len(current), "words": list(current)}
    except dict_store.DictStoreError as exc:
        ctx.issues.append(Issue(IssueLevel.ERROR, f"词典操作失败: {exc}"))
        ctx.outputs["dict_result"] = {"ok": False}


def step_render(ctx: RunContext) -> None:
    """落产物说明:explain 只写事实与计数,不写套话。"""
    report = ctx.outputs.get("report")
    explain: dict[str, object] = {
        "source_chars": ctx.outputs.get("source_chars", 0),
        "verdict": ctx.outputs.get("verdict", "NOT_RUN"),
    }
    if report is not None:
        by_rule: dict[str, int] = {}
        for row in report["hard"]:
            name = str(row["rule_name"])
            by_rule[name] = by_rule.get(name, 0) + 1
        explain["hard_count"] = report["hard_count"]
        explain["by_rule"] = dict(sorted(by_rule.items()))
    if "dict_result" in ctx.outputs:
        explain["dict_result"] = ctx.outputs["dict_result"]
    ctx.outputs["explain"] = explain
