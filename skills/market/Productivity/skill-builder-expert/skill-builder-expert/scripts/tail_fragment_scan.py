# -*- coding: utf-8 -*-
"""尾部兜底片段强制挂载扫描器（tail_fragment_scan）

规范落点：references/REF-USER-CONTROL-044_UserSenseCheck.md
片段逐字稿落点：references/REF-TMP-003_MenuInteraction.md#【公共兜底尾部片段 REF-TMP-TAIL-001】

规则（fail-closed，任一命中即 FAIL，退出码非 0）：
  F1 片段定义锚点必须存在，且片段正文与基准句一致（防改写/删减）；
  F2 所有对外输出模板块（标题含「【」且不属于对内豁免类）正文必须包含
     挂载标记 {{REF-TMP-TAIL-001}}；
  F3 状态机全局规则必须包含尾部片段强制挂载条目；
  F4 兜底片段文本禁止出现「您」（包内交互统一「你」口径，开场问候除外）。

支持 --self-test 阳/阴用例自测；自测不过则其 PASS 结论无效。
"""
import sys
import re
from pathlib import Path

MARKER = "{{REF-TMP-TAIL-001}}"
FRAG_ANCHOR = "【公共兜底尾部片段 REF-TMP-TAIL-001】"
# 基准句：片段正文中必须逐句存在（防模型/人工改写丢失出口）
BASELINE_LINES = [
    "如果你不清楚接下来如何操作，可回复 **【帮助】** 唤起完整导航",
    "拿不定主意可以直接说出你的顾虑",
    "随时回复 **【菜单】** 或者数字 **【0】**，回到主菜单选择服务项数字，开始为你技能代建、技能答疑、技能优化、技能评测",
]
SM_RULE_KEY="<REDACTED>"
SM_RULE_DOC = "REF-USER-CONTROL-044"
# 对内豁免类：标题命中任一关键词则不要求挂载标记
INTERNAL_KEYS = ("对内", "话术池", "措辞库", "铁律", "铁则")


def is_external_block(heading: str) -> bool:
    """对外模板块判定：标题含【且不属对内豁免类。"""
    if "【" not in heading:
        return False
    return not any(k in heading for k in INTERNAL_KEYS)


def iter_blocks(text: str):
    """按二级标题切块，产出 (标题行, 块全文)。"""
    lines = text.replace("\r\n", "\n").split("\n")
    cur_head, cur_buf = None, []
    for ln in lines:
        if ln.startswith("## "):
            if cur_head is not None:
                yield cur_head, "\n".join(cur_buf)
            cur_head, cur_buf = ln, []
        else:
            if cur_head is not None:
                cur_buf.append(ln)
    if cur_head is not None:
        yield cur_head, "\n".join(cur_buf)


def run_checks(root):
    """返回违例消息列表；空列表 = PASS。"""
    root = Path(root)
    msgs = []
    tmp = root / "references" / "REF-TMP-003_MenuInteraction.md"
    if not tmp.is_file():
        return ["F0 模板总册缺失: %s" % tmp]
    text = tmp.read_bytes().decode("utf-8")

    # F1 片段定义锚点与基准句
    frag_block = None
    for head, body in iter_blocks(text):
        if FRAG_ANCHOR in head:
            frag_block = body
            break
    if frag_block is None:
        msgs.append("F1 片段定义锚点缺失: %s" % FRAG_ANCHOR)
    else:
        for base in BASELINE_LINES:
            if base not in frag_block:
                msgs.append("F1 片段基准句缺失/被改写: %s" % base[:24])
        # F4 片段文本口径：包内交互统一「你」，禁止「您」
        if "您" in frag_block:
            msgs.append("F4 片段文本出现「您」（应为「你」口径）")

    # F2 对外模板块强制挂载
    checked = 0
    for head, body in iter_blocks(text):
        if head.strip().startswith("## 【公共兜底尾部片段"):
            continue  # 片段定义自身不挂载自身
        if not is_external_block(head):
            continue
        checked += 1
        if MARKER not in body:
            msgs.append("F2 对外模板缺尾部挂载标记: %s" % head.strip()[:40])
    if checked == 0:
        msgs.append("F2 未发现任何对外模板块（扫描逻辑异常，按 FAIL 处理）")

    # F3 状态机全局规则条目
    sm = root / "references" / "REF-SM-004_StateMachine.yaml"
    if sm.is_file():
        smt = sm.read_bytes().decode("utf-8")
        if SM_RULE_KEY not in smt or SM_RULE_DOC not in smt:
            msgs.append("F3 状态机缺少尾部片段强制挂载全局规则条目")
    else:
        msgs.append("F3 状态机文件缺失")

    # F5 内联执行位片段逐字稿强制（v171 品牌触点铁则：纯展示轮零额外读取，弹药必须随屏就地）
    INLINE_HEADS = [
        "#### 开场屏",
        "#### 档案管理子菜单内联",
        "#### [1] 代建入口首屏",
        "#### [2] 答疑入口首屏",
        "#### 【常见问题】目录大纲",
    ]
    sk = root / "SKILL.md"
    if not sk.is_file():
        msgs.append("F5 SKILL.md 缺失（内联执行位检查不可执行）")
    else:
        skt = sk.read_bytes().decode("utf-8")
        for pref in INLINE_HEADS:
            m = re.search(r"(?ms)^" + re.escape(pref) + r".*?(?=^#### |^### |\Z)", skt)
            if not m:
                msgs.append("F5 内联屏块缺失: %s" % pref)
                continue
            blk = m.group(0)
            if "\U0001F4A1小提示：" not in blk:
                msgs.append("F5 内联屏缺尾部片段逐字稿: %s" % pref)
            if "—— Skill技能搭建专家" not in blk:
                msgs.append("F5 内联屏缺统一落款: %s" % pref)
    dat = root / "references" / "REF-DAT-057_DirectAnswerTable.md"
    for lbl, pth in (("TMP", tmp), ("DAT", dat)):
        if not pth.is_file():
            msgs.append("F5 %s 文件缺失: %s" % (lbl, pth.name))
            continue
        b = pth.read_bytes().decode("utf-8")
        m = re.search(r"(?ms)^## 【欢迎启动菜单】.*?(?=^## |\Z|^### )", b)
        if not m:
            msgs.append("F5 欢迎启动菜单块缺失: %s" % lbl)
        elif "\U0001F4A1小提示：" not in m.group(0):
            msgs.append("F5 欢迎启动菜单缺片段逐字稿: %s" % lbl)

    return msgs


def _self_test():
    """阳/阴用例：阴例（合规夹具）须 PASS，阳例（缺标记夹具）须 FAIL。"""
    import tempfile
    ok = True
    base_tmp = Path(__file__).resolve().parents[1] / "references" / "REF-TMP-003_MenuInteraction.md"
    base_sm = Path(__file__).resolve().parents[1] / "references" / "REF-SM-004_StateMachine.yaml"
    if not base_tmp.is_file() or not base_sm.is_file():
        print("SELF-TEST SKIP: 基准文件不存在（脱离包根运行）")
        return 0
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / "references").mkdir()
        # 阴例：原样拷贝 → 应 PASS
        (tdp / "references" / "REF-TMP-003_MenuInteraction.md").write_bytes(base_tmp.read_bytes())
        (tdp / "references" / "REF-SM-004_StateMachine.yaml").write_bytes(base_sm.read_bytes())
        _base_sk = Path(__file__).resolve().parents[1] / "SKILL.md"
        _base_dat = Path(__file__).resolve().parents[1] / "references" / "REF-DAT-057_DirectAnswerTable.md"
        if _base_sk.is_file():
            (tdp / "SKILL.md").write_bytes(_base_sk.read_bytes())
        if _base_dat.is_file():
            (tdp / "references" / "REF-DAT-057_DirectAnswerTable.md").write_bytes(_base_dat.read_bytes())
        if run_checks(tdp):
            print("SELF-TEST FAIL: 阴例（合规夹具）被判违例")
            for m in run_checks(tdp):
                print("   -", m)
            ok = False
        else:
            print("SELF-TEST 阴例 PASS（合规夹具 0 违例）")
        # 阳例：删掉一个模板的标记 → 应 FAIL
        t2 = base_tmp.read_bytes().decode("utf-8")
        first_ext = None
        for head, _body in iter_blocks(t2):
            if is_external_block(head) and "公共兜底尾部片段" not in head:
                first_ext = head
                break
        lines = t2.replace("\r\n", "\n").split("\n")
        in_blk = False
        out = []
        for ln in lines:
            if ln.startswith("## "):
                in_blk = ln.strip() == first_ext.strip()
            if in_blk and MARKER in ln:
                continue  # 阳例：删除该块内全部挂载标记行
            out.append(ln)
        (tdp / "references" / "REF-TMP-003_MenuInteraction.md").write_bytes(
            "\n".join(out).encode("utf-8"))
        if run_checks(tdp):
            print("SELF-TEST 阳例 PASS（缺失标记被真实拦截）")
        else:
            print("SELF-TEST FAIL: 阳例（缺标记夹具）未被拦截")
            ok = False
    return 0 if ok else 1


def main():
    if "--self-test" in sys.argv:
        return _self_test()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    msgs = run_checks(root)
    if msgs:
        print("FAIL 尾部兜底片段扫描: %d 项" % len(msgs))
        for m in msgs:
            print("  - %s" % m)
        return 1
    print("PASS 尾部兜底片段扫描（片段锚点/基准句/对外模板挂载/状态机规则/口径 全部通过）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
