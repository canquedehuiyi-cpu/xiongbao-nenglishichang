"""
validator.py —— 数据标准化引擎（确定性，零 LLM）

职责：把各企业格式各异的真实数据文件（Excel/CSV 表格）自动识别列名、清洗值，
转成目标场景的标准键值行；同时产出回填模板所需的结构化数据与清洗报告。

80-20 原则：不追求识别任意版式，只覆盖"关键字段的常见列名"（中文为主、
英文为辅）。列名对不上时如实进报告转人工，绝不臆造值。

边界：只吃文本层；表格格值命中扫描件特征（图片/截图/扫描 等）时拒绝并转人工，
不输出伪数据；不做任何数值换算/口径假设。
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TableSpec:
    name: str                        # 输出模板表名
    prefix: str | None               # 键值行前缀；None=原文表（逐行输出文本）
    headers: tuple[str, ...]         # 标准列头（= INPUT_CONTRACT 键）
    aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)  # 标准列 -> 常见列名


@dataclass(frozen=True)
class SceneSpec:
    snake: str                       # 目标场景目录名
    display: str                     # 场景显示名（报告用）
    tables: tuple[TableSpec, ...]    # 可识别的表集合
    decl_headers: tuple[str, ...] = ()  # 输出模板附带的"口径声明"表头（物料场景）


# 扫描件/截图占位特征：格值命中即拒绝转人工（不输出伪数据）
_SCAN_HINTS = ("图片", "截图", "扫描", "拍照", "照片", "ocr", "image", "png", "jpg", "jpeg", "pdf扫描")


def _norm_header(value: str) -> str:
    """表头归一：全半角 + 小写 + 去空白/下划线/连字符。"""
    s = unicodedata.normalize("NFKC", value or "").strip().lower()
    return "".join(ch for ch in s if ch not in " _-／/（()）")


def _clean_value(value: str) -> str:
    """值清洗：全半角 + 首尾空白；千分位逗号等内部字符原样保留（防错列）。"""
    return unicodedata.normalize("NFKC", value or "").strip()


def _is_scan_cell(value: str) -> bool:
    s = value.lower()
    return any(h in s for h in _SCAN_HINTS)


# ---------------------------------------------------------------------------
# 场景键集与列名别名库（与 template_gen.py 的模板表头保持同源，tests 锁定一致性）
# ---------------------------------------------------------------------------

SCENES: dict[str, SceneSpec] = {
    "supplier_identity_vet": SceneSpec(
        snake="supplier_identity_vet",
        display="供应商核验",
        tables=(
            TableSpec(
                name="台账",
                prefix="台账:",
                headers=("名称", "法定代表人", "开户行", "统一社会信用代码"),
                aliases={
                    "名称": ("名称", "公司名称", "供应商名称", "单位名称", "企业名称", "name", "company"),
                    "法定代表人": ("法定代表人", "法人", "法人代表", "法定代表人姓名", "负责人"),
                    "开户行": ("开户行", "开户银行", "银行", "基本户开户行", "账户开户行"),
                    "统一社会信用代码": ("统一社会信用代码", "信用代码", "社会信用代码",
                                          "统一信用代码", "代码", "uscc", "credit code"),
                },
            ),
        ),
    ),
    "shipping_doc_crosscheck": SceneSpec(
        snake="shipping_doc_crosscheck",
        display="单证交叉核对",
        tables=(
            TableSpec(
                name="单证表",
                prefix="单证:",
                headers=("类型", "品名", "型号", "数量", "单价", "金额", "件数", "箱数",
                         "毛重", "净重", "体积", "币种", "柜号", "唛头", "起运港", "目的港",
                         "发货人", "收货人", "付款节点", "海运条款", "包装要求"),
                aliases={
                    "类型": ("类型", "单据类型", "单据", "单证类型", "type", "doc type"),
                    "品名": ("品名", "货物名称", "货名", "商品名称", "description", "goods"),
                    "型号": ("型号", "规格型号", "规格", "model", "spec"),
                    "数量": ("数量", "件数", "qty", "quantity", "pcs"),
                    "单价": ("单价", "unit price", "price"),
                    "金额": ("金额", "总金额", "amount", "total"),
                    "件数": ("件数", "总件数", "packages"),
                    "箱数": ("箱数", "总箱数", "cartons", "ctns"),
                    "毛重": ("毛重", "gross weight", "g.w."),
                    "净重": ("净重", "net weight", "n.w."),
                    "体积": ("体积", "容积", "volume", "cbm"),
                    "币种": ("币种", "货币", "币别", "currency", "ccy"),
                    "柜号": ("柜号", "集装箱号", "container no", "cntr"),
                    "唛头": ("唛头", "mark", "shipping mark"),
                    "起运港": ("起运港", "装运港", "port of loading", "pol"),
                    "目的港": ("目的港", "卸货港", "port of destination", "pod"),
                    "发货人": ("发货人", "托运人", "shipper"),
                    "收货人": ("收货人", "consignee"),
                    "付款节点": ("付款节点", "付款方式", "payment term", "付款条件"),
                    "海运条款": ("海运条款", "贸易条款", "incoterm", "价格条款"),
                    "包装要求": ("包装要求", "packing requirement", "包装"),
                },
            ),
        ),
    ),
    "material_kitting_check": SceneSpec(
        snake="material_kitting_check",
        display="物料齐套核对",
        decl_headers=("键", "值", "说明"),
        tables=(
            TableSpec(
                name="订单",
                prefix="订单:",
                headers=("订单号", "成品", "型号", "数量", "单位"),
                aliases={
                    "订单号": ("订单号", "订单编号", "销售订单", "so号", "so no", "工单号"),
                    "成品": ("成品", "产品名称", "物料名称", "品名", "成品名称"),
                    "型号": ("型号", "规格型号", "规格", "model"),
                    "数量": ("数量", "订单数量", "qty", "quantity"),
                    "单位": ("单位", "计量单位", "unit"),
                },
            ),
            TableSpec(
                name="BOM",
                prefix="BOM:",
                headers=("成品", "型号", "子件", "编码", "用量", "单位"),
                aliases={
                    "成品": ("成品", "产品名称", "父件", "母件"),
                    "型号": ("型号", "规格", "model"),
                    "子件": ("子件", "物料名称", "组件", "零部件", "bom物料"),
                    "编码": ("编码", "物料编码", "料号", "零件号", "code", "part no"),
                    "用量": ("用量", "单位用量", "数量", "qty", "usage"),
                    "单位": ("单位", "计量单位", "unit"),
                },
            ),
            TableSpec(
                name="库存",
                prefix="库存:",
                headers=("编码", "名称", "数量", "单位", "批次"),
                aliases={
                    "编码": ("编码", "物料编码", "料号", "库存编码", "code", "part no"),
                    "名称": ("名称", "物料名称", "品名", "货物名称"),
                    "数量": ("数量", "库存数量", "结存数量", "qty", "on hand"),
                    "单位": ("单位", "计量单位", "unit"),
                    "批次": ("批次", "批号", "lot no", "batch", "库位"),
                },
            ),
            TableSpec(
                name="在途",
                prefix="在途:",
                headers=("编码", "名称", "数量", "单位", "批次", "交期"),
                aliases={
                    "编码": ("编码", "物料编码", "料号", "code", "part no"),
                    "名称": ("名称", "物料名称", "品名"),
                    "数量": ("数量", "在途数量", "采购数量", "qty"),
                    "单位": ("单位", "计量单位", "unit"),
                    "批次": ("批次", "批号", "lot no", "采购批次"),
                    "交期": ("交期", "预计到货", "到货日期", "交期日期", "eta", "delivery date"),
                },
            ),
        ),
    ),
    "external_statement_reconcile": SceneSpec(
        snake="external_statement_reconcile",
        display="外部对账",
        tables=(
            TableSpec(
                name="流水表",
                prefix="流水:",
                headers=("日期", "客户", "金额", "单号", "类型", "摘要"),
                aliases={
                    "日期": ("日期", "交易时间", "交易日期", "记账日期", "发生日期", "date"),
                    "客户": ("客户", "客户名称", "户名", "对方单位", "往来单位", "交易对手",
                             "counterparty", "customer"),
                    "金额": ("金额", "发生额", "发生金额", "交易金额", "借方金额", "贷方金额", "amount"),
                    "单号": ("单号", "流水号", "凭证号", "交易号", "参考号", "ref no"),
                    "类型": ("类型", "借贷", "方向", "借贷标志", "收支", "借/贷", "side"),
                    "摘要": ("摘要", "备注", "用途", "说明", "memo", "narration"),
                },
            ),
            TableSpec(
                name="订单表",
                prefix="订单:",
                headers=("日期", "客户", "金额", "单号", "摘要"),
                aliases={
                    "日期": ("日期", "下单日期", "订单日期", "开票日期", "date"),
                    "客户": ("客户", "客户名称", "购货方", "购买方", "单位名称"),
                    "金额": ("金额", "订单金额", "含税金额", "开票金额", "amount"),
                    "单号": ("单号", "订单号", "发票号", "单据号", "invoice no", "order no"),
                    "摘要": ("摘要", "品名", "货物名称", "备注", "memo"),
                },
            ),
        ),
    ),
    "bid_deviation_crosscheck": SceneSpec(
        snake="bid_deviation_crosscheck",
        display="偏离核对",
        tables=(
            TableSpec(
                name="方案正文",
                prefix=None,  # 原文表：逐行输出文本
                headers=("原文",),
            ),
            TableSpec(
                name="偏离表",
                prefix="偏离:",
                headers=("条目", "声明", "关键词", "依据"),
                aliases={
                    "条目": ("条目", "偏离条目", "项目", "内容", "item"),
                    "声明": ("声明", "偏离声明", "应答", "响应", "偏离情况", "declaration"),
                    "关键词": ("关键词", "关键词组", "检索词", "关键字", "keyword"),
                    "依据": ("依据", "章节依据", "响应章节", "页码", "reference"),
                },
            ),
        ),
    ),
    "bid_disqualification_terms": SceneSpec(
        snake="bid_disqualification_terms",
        display="投标要件核对",
        tables=(
            TableSpec(
                name="招标文件",
                prefix=None,  # 原文表：逐行输出文本
                headers=("原文",),
            ),
            TableSpec(
                name="条款清单",
                prefix="条款:",
                headers=("名称", "关键词", "材料", "类别"),
                aliases={
                    "名称": ("名称", "条款名称", "要件名称", "检查项", "资格项"),
                    "关键词": ("关键词", "检索词", "关键词组", "keyword"),
                    "材料": ("材料", "证明材料", "要求材料", "附件材料", "提交材料"),
                    "类别": ("类别", "类型", "性质", "条款类型", "硬性/加分"),
                },
            ),
            TableSpec(
                name="材料清单",
                prefix="材料:",
                headers=("名称", "关键词"),
                aliases={
                    "名称": ("名称", "材料名称", "文件名", "资料名称"),
                    "关键词": ("关键词", "检索词", "keyword"),
                },
            ),
            TableSpec(
                name="应然清单",
                prefix="文件:",
                headers=("名称", "关键词", "必须"),
                aliases={
                    "名称": ("名称", "文件名称", "资料名称", "应提供项"),
                    "关键词": ("关键词", "检索词", "keyword"),
                    "必须": ("必须", "是否必须", "必需", "必交", "required"),
                },
            ),
        ),
    ),
}


def _build_reverse_index(spec: SceneSpec) -> dict[str, list[tuple[int, int]]]:
    """别名反查表：归一化列名 -> [(表序号, 标准列序号), ...]。"""
    rev: dict[str, list[tuple[int, int]]] = {}
    for ti, table in enumerate(spec.tables):
        for ci, std in enumerate(table.headers):
            names = (std,) + table.aliases.get(std, ())
            for n in dict.fromkeys(names):  # 去重（别名元组首项=标准列名，会重复）
                key = _norm_header(n)
                if key:
                    rev.setdefault(key, []).append((ti, ci))
    return rev


def select_table(header: list[str], spec: SceneSpec) -> tuple[int | None, list[str]]:
    """按命中率+专属命中选表；返回 (表序号或 None, 未识别列名清单)。

    评分：(命中率, 专属命中数, 命中总数)——命中率优先，避免"列多的表吃掉
    列少的表"（如订单表 5 列被流水表 6 列覆盖）。
    """
    rev = _build_reverse_index(spec)
    norms = [_norm_header(h) for h in header]
    best: int | None = None
    best_score: tuple[float, int, int] | None = None
    for ti, table in enumerate(spec.tables):
        if table.prefix is None:  # 原文表不参与表格匹配，走兜底
            continue
        hit_total = 0
        hit_exclusive = 0
        for key in norms:
            targets = rev.get(key, [])
            if not targets:
                continue
            hit_self = [t for t in targets if t[0] == ti]
            if not hit_self:  # 该列没命中本表，不计入本表
                continue
            hit_total += 1
            if len(hit_self) == len(targets):
                hit_exclusive += 1
        if hit_total == 0:
            continue
        score = (hit_total / len(table.headers), hit_exclusive, hit_total)
        if best_score is None or score > best_score:
            best, best_score = ti, score
    unknown = [h for h, key in zip(header, norms) if key not in rev]
    return best, unknown


def normalize_table(
    rows: list[list[str]],
    spec: SceneSpec,
) -> dict:
    """表格输入标准化：选表 -> 列映射 -> 键值行 + 回填数据 + 报告。"""
    if not rows or not rows[0]:
        return _result(spec, [], {}, {"错误": ["输入表为空"]})
    header = [_clean_value(h) for h in rows[0]]
    ti, unknown_cols = select_table(header, spec)
    report: dict[str, list[str]] = {"未识别列": unknown_cols or ["（无，列名全部识别）"]}
    if ti is None:
        plain = next((t for t in spec.tables if t.prefix is None), None)
        if plain is not None:
            lines = [" ".join(_clean_value(c) for c in r if _clean_value(c)) for r in rows[1:]]
            lines = [ln for ln in lines if ln]
            return _result(spec, lines, {}, report)
        return _result(spec, [], {}, {**report, "错误": ["表头列名无法识别，且该场景无原文表兜底，请改用模板或文本输入"]})
    table = spec.tables[ti]
    rev = _build_reverse_index(spec)
    # 标准列 -> 输入列
    col_map: dict[int, int] = {}
    for in_col, key in enumerate(_norm_header(h) for h in header):
        for t2, c2 in rev.get(key, []):
            if t2 == ti:
                col_map.setdefault(c2, in_col)
    out: list[str] = []
    backfill: list[list] = []
    manual: list[str] = []
    for idx, r in enumerate(rows[1:], start=2):
        kv: list[tuple[int, str]] = []
        row_manual: list[str] = []
        for std_i, in_col in sorted(col_map.items()):
            val = _clean_value(r[in_col]) if in_col < len(r) else ""
            if not val:
                continue
            if _is_scan_cell(val):
                row_manual.append(f"表[{table.name}] 第{idx}行 列[{table.headers[std_i]}] 含扫描件占位：{val}")
                continue
            kv.append((std_i, val))
        if row_manual:
            manual.extend(row_manual)  # 扫描件所在行整行拒出，不产伪数据
            continue
        if kv:
            row = dict(kv)
            if spec.snake == "supplier_identity_vet":
                # 两侧对照按字段逐行输出（与模板/文本契约同构）
                out.extend(f"{table.prefix}{table.headers[i]}={v}" for i, v in kv)
            else:
                out.append(table.prefix + " ".join(f"{table.headers[i]}={v}" for i, v in kv))
            backfill.append([row.get(i, "") for i in range(len(table.headers))])
    if manual:
        report["转人工"] = manual
    mapping = {table.headers[ci]: header[i] for ci, i in sorted(col_map.items())}
    return _result(spec, out, backfill, report, table_index=ti, col_map=mapping)


def normalize_text(lines: list[str], spec: SceneSpec) -> dict:
    """非表格输入（文本/PDF/Word）：清洗后按文本行输出（原文行语义不变）。"""
    out = [_clean_value(ln) for ln in lines if _clean_value(ln)]
    report = {"说明": ["非表格输入：按文本行原样输出，交由目标场景解析（扫描件请先转文本层）"]}
    return _result(spec, out, [], report)


def _result(spec: SceneSpec, lines: list[str], backfill: list[list],
            report: dict, table_index: int | None = None,
            col_map: dict[str, str] | None = None) -> dict:
    return {
        "lines": lines,
        "backfill": backfill,
        "report": report,
        "table_index": table_index,
        "col_map": col_map or {},
        "tables": spec.tables,
        "scene": spec,
    }


def backfill_sheets(result: dict) -> list[tuple[str, list[str], list[list]]]:
    """产出回填模板：表名/表头与目标场景 template_reader 对齐，产物可回喂判定。

    命中表填数据行；原文表回填文本行；未命中表留空仅表头；supplier 场景按
    「两侧对照」纵向结构转换；material 场景附空「口径声明」表供用户后补。
    """
    scene: SceneSpec = result["scene"]
    lines: list[str] = result["lines"]
    backfill: list[list] = result["backfill"]
    table_index: int | None = result["table_index"]
    tables: tuple[TableSpec, ...] = result["tables"]

    if scene.snake == "supplier_identity_vet":
        headers = tables[0].headers
        rows = [[std, dict(zip(headers, d)).get(std, ""), ""] for d in backfill for std in headers]
        return [("两侧对照", ["字段", "台账侧", "证照侧"], rows)]

    sheets: list[tuple[str, list[str], list[list]]] = []
    for i, t in enumerate(tables):
        if t.prefix is None:
            sheets.append((t.name, list(t.headers), [[ln] for ln in lines]))
        elif i == table_index:
            sheets.append((t.name, list(t.headers), backfill))
        else:
            sheets.append((t.name, list(t.headers), []))
    if scene.decl_headers:
        sheets.append(("口径声明", list(scene.decl_headers), []))
    return sheets
