"""策略结果构造模块。

每个策略文件包含一个或多个策略判定函数，统一返回
{code, name, passed, score, signal_strength, reasons, details} 七字段字典，
确保组合引擎可统一调用、报告层可统一消费。
"""


def clean_klines(klines: list) -> list:
    """剔除关键字段（open/close/high/low/volume）为 None 或非数值的无效 K 线。

    数据源字段缺失或类型异常时如实剔除，避免后续判定对 None/字符串做运算崩溃；
    正常数据（字段完整且为数值）不受影响。非 dict 行/None 行一并剔除（防御异常输入）；
    klines 为 None 时返回空列表（策略判定入口统一以空K线处理，零崩溃）。
    类型契约：正常 K 线数值字段经数据层 safe_float 强制为 float/int；
    字符串等非数值行在此统一剔除，保证任何入参下策略判定零类型崩溃。
    """
    if not klines:
        return []
    return [
        k for k in klines
        if isinstance(k, dict)
        and all(
            isinstance(k.get(f), (int, float)) and not isinstance(k.get(f), bool)
            for f in ("open", "close", "high", "low", "volume")
        )
    ]


def clean_fundamental(fundamental) -> dict:
    """数值化基本面字段：非数值/占位符统一为 None，保证策略比较零类型崩溃。

    与数据层 fundamental._num 口径一致：
    - None、''、'-'、'--' 等占位符 → None（下游策略以 `is not None` 判缺）
    - 数字（int/float，不含 bool）→ float
    - 其他类型（字符串/对象等）→ None
    fundamental 非 dict（None/列表等）→ 返回空 dict。

    Args:
        fundamental: 基本面字段字典（可能为 None）

    Returns:
        dict: 字段全部为 None 或 float 的干净字典
    """
    if not isinstance(fundamental, dict):
        return {}
    out = {}
    for key, val in fundamental.items():
        if val is None:
            out[key] = None
        elif isinstance(val, bool):
            out[key] = None
        elif isinstance(val, (int, float)):
            out[key] = float(val)
        elif isinstance(val, str) and val.strip() in ("", "-", "--"):
            out[key] = None
        else:
            out[key] = None
    return out


def make_result(code: str, name: str, passed: bool, score: float,
                reasons: list = None, details: dict = None,
                signal_strength: str = None) -> dict:
    """快捷构造策略判定结果字典。

    Args:
        code: 策略编号（与注册表键一致，如 'S01'）
        name: 策略名称
        passed: 是否通过
        score: 归一化得分
        reasons: 判定理由列表
        details: 详细判定数据
        signal_strength: 信号强度 '强'/'中'/'弱'；None 表示未达到任何信号级别

    Returns:
        dict: {code, name, passed, score, signal_strength, reasons, details}

    契约：
    - 失败策略（passed=False 且 score<=0）signal_strength 恒为 None；
    - 仅当 score>0 时才按分值推导 '弱'/'中'/'强'，避免失败策略被误标为弱信号。
    """
    if signal_strength is None and score > 0:
        signal_strength = "强" if score >= 0.7 else ("中" if score >= 0.4 else "弱")
    det = details or {}
    if "conditions" not in det:
        det["conditions"] = {}
    return {
        "code": code,
        "name": name,
        "passed": passed,
        "score": round(score, 4),
        "signal_strength": signal_strength,
        "reasons": reasons or [],
        "details": det,
    }
