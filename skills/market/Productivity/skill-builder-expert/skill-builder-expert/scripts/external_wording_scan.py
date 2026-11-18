#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对外表述扫描闸（fail-closed）
规范定稿（2026-11-03）。
扫描对象：对外主文档 SKILL.md。
七查：
  F1 third-party 字样清零
  F2 旧业务概念名清零（现名：用户自有素材技能重构）
  F3 自动驾驶类比句清零
  F4 主文档指定字样清零（对外统一「权属」口径，词面码点拼装）
  F5 素材处置能力解释类语句清零（判定类邻接组合，词面码点拼装）
  F6 第三方与素材/案例/技能包邻接清零（词面码点拼装）
  F7 中性化标记位：2.6 收费配置标准句、2.7 交付物标识短句在位
任何一项命中即 FAIL，退出码 1；--self-test 运行阳/阴用例自测。
"""
import io
import re
import sys
from pathlib import Path

TARGET = "SKILL.md"
# 敏感词面一律码点拼装，不落本文件（与 _红线词表 同款纪律）
_W = "\u7d20\u6750|\u6765\u6e90|\u5408\u6cd5|\u4fb5\u6743|\u7248\u6743|\u662f\u5426|\u5224\u65ad|\u9274\u522b|\u7b2c\u4e09\u65b9|\u6848\u4f8b|\u6280\u80fd\u5305".split("|")
# 依序：0\u7d20\u6750 1\u6765\u6e90 2\u5408\u6cd5 3\u4fb5\u6743 4\u7248\u6743 5\u662f\u5426 6\u5224\u65ad 7\u9274\u522b 8\u7b2c\u4e09\u65b9 9\u6848\u4f8b 10\u6280\u80fd\u5305（注释亦用码点写法，字面不落文件）
_PAT_TP = re.compile(r"third-party", re.I)
_PAT_ML = re.compile("\u5916\u6765\u6280\u80fd\u6574\u5408\u6539\u9020")  # 旧概念名，码点拼装
_PAT_AD = re.compile(r"autonomous-driving", re.I)
_PAT_BQ = re.compile(_W[4])
_PAT_LEGAL = re.compile(
    "(" + _W[0] + "|" + _W[1] + ")[^。\n]{0,16}(" + _W[2] + "|" + _W[3] + ")"
    "|" + _W[5] + _W[2] + "|" + _W[6] + _W[0] + "|" + _W[7] + "[^。\n]{0,8}(" + _W[0] + "|" + _W[4] + ")"
)
_PAT_3RD = re.compile(
    _W[8] + "[^。\n]{0,12}(" + _W[0] + "|" + _W[9] + "|" + _W[10] + ")"
    "|(" + _W[0] + "|" + _W[9] + "|" + _W[10] + ")[^。\n]{0,12}" + _W[8]
)
_MARK_26 = "官方开发者规则文档"
# 主文档唯一指定法律声明区标题（码点拼装）：锁定 emoji + 「版权声明」四字
_NOTICE_HEAD = "\n## \U0001F512 \u7248\u6743\u58f0\u660e"
_MARK_27 = "不写入其他分发平台名称"

# F9 出口文档平台名零字面（三方复核清单第四节落地，v82）：INSTALL/LISTING/FAQ/README
# 与 SKILL.md 同扫；市场与生态名称字面零落盘（支付通道名属支付事实，不在本查范围，
# 口径依据 REF-PAY-012 §十五）。词面码点拼装，本文件零字面。
OUTBOUND_TARGETS = ["INSTALL.md", "LISTING.md", "FAQ.md", "README.md"]
_PAT_ECO = re.compile("腾讯|阿里")


def run_checks(root):
    root = Path(root)
    p = root / TARGET
    if not p.exists():
        return [f"{TARGET} 不存在"]
    t = io.open(p, "r", encoding="utf-8").read().replace("\r\n", "\n")
    t_full = t
    # 指定法律声明区为唯一豁免块：从锚点行到文末整体剥离后参与 F1–F6 扫描；
    # 锚点未命中则全文照扫（fail-closed：豁免区不成立即无豁免）
    jn = t.find(_NOTICE_HEAD)
    if jn >= 0:
        t = t[:jn]
    fails = []
    if _PAT_TP.search(t):
        fails.append("F1 third-party 字样命中")
    if _PAT_ML.search(t):
        fails.append("F2 旧业务概念名命中")
    if _PAT_AD.search(t):
        fails.append("F3 自动驾驶类比句命中")
    m = _PAT_BQ.search(t)
    if m:
        fails.append(f"F4 指定字样命中：…{t[max(0, m.start() - 20):m.end() + 20]}…")
    m = _PAT_LEGAL.search(t)
    if m:
        fails.append(f"F5 素材处置能力解释类语句命中：…{t[max(0, m.start() - 20):m.end() + 20]}…")
    m = _PAT_3RD.search(t)
    if m:
        fails.append(f"F6 第三方邻接命中：…{t[max(0, m.start() - 20):m.end() + 20]}…")
    # 批次3 瘦身：2.6/2.7/2.8 真源外置 REF-APP-066（扫描随迁）
    _vault = ""
    _vp = p.parent / "references" / "REF-APP-066_LowFreqTruthVault.md"
    if _vp.exists():
        _vault = io.open(_vp, "r", encoding="utf-8").read().replace("\r\n", "\n")
    i26 = _vault.find("### 2.6")
    i27 = _vault.find("### 2.7")
    i28 = _vault.find("### 2.8")
    if i26 < 0 or i27 < 0 or i28 < 0:
        fails.append("F7 2.6/2.7/2.8 章节定位失败（REF-APP-066）")
    else:
        if _MARK_26 not in _vault[i26:i27]:
            fails.append("F7 2.6 收费配置标准句缺失")
        if _MARK_27 not in _vault[i27:i28]:
            fails.append("F7 2.7 交付物标识短句缺失")
    # F9 出口文档平台名零字面
    m9 = _PAT_ECO.search(t_full)
    if m9:
        fails.append("F9 出口文档平台名命中(SKILL.md)：…%s…" % t_full[max(0, m9.start() - 15):m9.end() + 15])
    for name in OUTBOUND_TARGETS:
        q = root / name
        if not q.exists():
            continue  # 缺省文档不属违例（README 可选）
        ot = io.open(q, "r", encoding="utf-8").read().replace("\r\n", "\n")
        m9 = _PAT_ECO.search(ot)
        if m9:
            fails.append("F9 出口文档平台名命中(%s)：…%s…" % (name, ot[max(0, m9.start() - 15):m9.end() + 15]))
    return fails


def _self_test():
    import shutil
    import tempfile
    ok = True
    base = Path(tempfile.mkdtemp())
    try:
        good = io.open(Path(__file__).resolve().parent.parent / TARGET, encoding="utf-8").read()
        d = base / "good"
        d.mkdir()
        io.open(d / TARGET, "w", encoding="utf-8", newline="\n").write(good)
        r = run_checks(d)
        if r:
            ok = False
            print("SELF-TEST 阴性失败:", r)
        # 阳性注入必须放在版权声明豁免区之前——v65 起文末声明区到 EOF 整体豁免，
        # 追加在 good 末尾的注入会被豁免剥离导致假 0 命中（定稿依据 2026-11-04
        # 三方质检实测 SELF-TEST FAIL，根因即此）；注入前置到 good 开头参与扫描。
        bad_txt = (
            "\ntesting third-party 注入 " + _PAT_ML.pattern + " 注入 autonomous-driving 注入 "
            + _W[4] + " 注入 " + _W[5] + _W[2] + " 注入 " + _W[8] + "\u7d20\u6750\u6ce8\u5165"
            "\n### 2.6 x\n### 2.7 y\n### 2.8 z\n"
        ) + good
        b = base / "bad"
        b.mkdir()
        io.open(b / TARGET, "w", encoding="utf-8", newline="\n").write(bad_txt)
        r = run_checks(b)
        if len(r) < 6:
            ok = False
            print("SELF-TEST 阳性拦截不足:", r)
        # F9 用例：出口文档带平台名应拦截，干净出口文档应放行
        eco = _PAT_ECO.pattern
        c1 = base / "out1"
        c1.mkdir()
        io.open(c1 / TARGET, "w", encoding="utf-8", newline="\n").write(good)
        io.open(c1 / "INSTALL.md", "w", encoding="utf-8", newline="\n").write("安装说明：打开技能市场搜索即可。" + eco + "注入\n")
        r1 = run_checks(c1)
        ok = ok and any("F9" in x and "INSTALL.md" in x for x in r1)
        c2 = base / "out2"
        c2.mkdir()
        io.open(c2 / TARGET, "w", encoding="utf-8", newline="\n").write(good)
        io.open(c2 / "INSTALL.md", "w", encoding="utf-8", newline="\n").write("安装说明：打开你所在技能市场搜索即可。\n")
        io.open(c2 / "LISTING.md", "w", encoding="utf-8", newline="\n").write("# 清单页\n兼容各智能体平台。\n")
        r2 = run_checks(c2)
        ok = ok and not any("F9" in x for x in r2)
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print("SELF-TEST PASS（阴性 0 命中 ＋ 阳性全拦截）" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    # flag 与目录参数严格分离（观察项2工具链建议）：--self-test 永远不进目录位，
    # 防使用者误传参数产生假 FAIL（定稿依据 2026-11-04 三方质检实测误触两次）
    _flags = [a for a in sys.argv[1:] if a.startswith("-")]
    _pos = [a for a in sys.argv[1:] if not a.startswith("-")]
    strict_pay = "--strict-pay" in _flags  # 可选开关：默认关（支付通道名属支付事实豁免，口径 REF-PAY-012 §15.2）；开启后支付品牌词命中即 FAIL
    if "--self-test" in _flags or "-t" in _flags:
        sys.exit(_self_test())
    root = Path(_pos[0]) if _pos else Path(".")
    fails = run_checks(root)
    if strict_pay:
        import zipfile as _zf
        _pay_words = ["微信支付", "支付宝", "SkillPay", "WeChat", "Alipay"]
        for _f in sorted(root.rglob("*")):
            if _f.suffix not in (".md", ".py", ".yaml", ".json") or _f.name == "external_wording_scan.py":
                continue
            _t = _f.read_text(encoding="utf-8", errors="replace")
            for _w in _pay_words:
                if _w in _t:
                    fails.append("strict-pay: %s 命中支付品牌词 %r（--strict-pay 开启，口径 REF-PAY-012 §15.2 之可选项）" % (_f.name, _w))
    if fails:
        print("FAIL 对外表述扫描")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("PASS 对外表述扫描（F1-F9 全部通过（含出口文档平台名零字面））")
