"""交易系统代码安全审计模块（静态扫描）。

面向交易系统/量化代码的安全扫描，检测：
- 硬编码 API 密钥 / 访问令牌 / 私钥（真实正则规则，非启发式猜测）
- 危险函数调用（eval/exec/动态代码、shell=True、反序列化等）
- SQL 注入风险（字符串拼接 SQL 无参数化）
- 弱传输/无超时等常见安全问题

定位：确定性静态规则扫描，输出可追溯的问题列表（文件:行号 + 匹配内容 + 修复建议）。
不执行被测代码，不修改被测文件；仅读取并分析。
"""

import os
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class Finding:
    """一条审计发现。"""
    file: str
    line: int
    rule: str
    severity: str  # 高/中/低
    match: str
    message: str
    fix: str = ""


@dataclass
class AuditResult:
    """一次审计的结果。"""
    findings: List[Finding] = field(default_factory=list)
    scanned_files: int = 0
    scanned_lines: int = 0

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "高")

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "中")

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "低")


# ── 规则定义：key -> (描述, 严重度, 正则, 修复建议) ──
_RULES: List[dict] = [
    {
        "rule": "API密钥/令牌硬编码",
        "severity": "高",
        "pattern": re.compile(
            r"(?i)(api[_-]?key|apikey|secret|token|access[_-]?key|auth[_-]?token"
            r"|app[_-]?secret|client[_-]?secret)\s*[=:]\s*['\"][^'\"]{6,}['\"]"
            r"|sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}"
            r"|xox[baprs]-[A-Za-z0-9-]{10,}"
        ),
        "fix": "将密钥移入环境变量/密钥管理服务，代码中仅引用 os.environ['KEY']；严禁把真实密钥提交进仓库。",
    },
    {
        "rule": "私钥/证书硬编码",
        "severity": "高",
        "pattern": re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|-----BEGIN CERTIFICATE-----"),
        "fix": "私钥应存放于受保护的文件并设置权限，通过密钥管理加载；移除代码中的明文私钥。",
    },
    {
        "rule": "明文密码",
        "severity": "高",
        "pattern": re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{1,}['\"]"),
        "fix": "使用环境变量或密钥管理存储密码；日志中禁止输出密码。",
    },
    {
        "rule": "危险动态执行",
        "severity": "高",
        "pattern": re.compile(r"\b(eval|exec)\s*\(|compile\s*\(.*['\"]exec|__import__\s*\("),
        "fix": "避免对不可信输入执行 eval/exec；需要动态执行时应白名单校验输入。",
    },
    {
        "rule": "shell 命令注入",
        "severity": "高",
        "pattern": re.compile(r"os\.system\s*\(|subprocess\.(run|call|Popen)\s*\([^)]*shell\s*=\s*True"),
        "fix": "使用 subprocess 列表参数形式（不传 shell=True），并严格校验外部输入。",
    },
    {
        "rule": "不安全反序列化",
        "severity": "高",
        "pattern": re.compile(r"pickle\.loads?\s*\(|yaml\.load\s*\([^)]*Loader\s*=\s*[^)]*|shelve\.open\s*\("),
        "fix": "反序列化不可信数据可导致代码执行；改用 json/safe_load 或校验来源。",
    },
    {
        "rule": "SQL 注入（字符串拼接）",
        "severity": "高",
        "pattern": re.compile(
            r"(?i)(SELECT|INSERT|UPDATE|DELETE|WHERE).{0,60}(f['\"]|\.format\(|%s|['\"]\s*\+|\+\s*['\"])"
        ),
        "fix": "使用参数化查询（占位符 %s/?）或 ORM，禁止拼接外部输入到 SQL。",
    },
    {
        "rule": "HTTP 请求无超时",
        "severity": "中",
        "pattern": re.compile(r"requests\.(get|post|put|delete|patch|head)\s*\("),
        "fix": "为所有网络请求设置超时（requests.get(url, timeout=5)），避免线程/任务挂死。",
    },
    {
        "rule": "弱随机数",
        "severity": "中",
        "pattern": re.compile(r"\brandom\.(random|randint|choice|uniform)\s*\("),
        "fix": "安全敏感场景（如交易随机偏移）应使用 secrets / random.SystemRandom。",
    },
    {
        "rule": "硬编码数据库地址/凭据",
        "severity": "中",
        "pattern": re.compile(r"(?i)(mysql|postgres|redis|mongodb)://[^\s'\"]+:[^\s'\"@]+@"),
        "fix": "数据库连接串中的密码不应硬编码，改用环境变量注入。",
    },
    {
        "rule": "日志泄露敏感字段",
        "severity": "中",
        "pattern": re.compile(r"logging\.(info|debug|warning|error).{0,80}(api_key|secret|password|token)"),
        "fix": "日志中禁止输出密钥/口令；必要时脱敏（仅保留后4位）。",
    },
    {
        "rule": "异常信息泄露内部细节",
        "severity": "低",
        "pattern": re.compile(r"print\s*\(.*str\(e\)|traceback\.print_exc\s*\(\)"),
        "fix": "对外暴露原始堆栈可能泄露内部结构；记录到日志而非返回给用户。",
    },
]


def _check_line(line: str, lineno: int, fpath: str, result: AuditResult) -> None:
    """对单行应用全部规则。"""
    for rule in _RULES:
        m = rule["pattern"].search(line)
        if m:
            # HTTP 无超时规则：行内已含 timeout= 视为已设超时，豁免
            if rule["rule"] == "HTTP 请求无超时" and "timeout" in line:
                continue
            matched = m.group(0)
            result.findings.append(Finding(
                file=fpath,
                line=lineno,
                rule=rule["rule"],
                severity=rule["severity"],
                match=matched[:80],
                message=f"发现{rule['rule']}：{matched[:60]}",
                fix=rule["fix"],
            ))


def audit_file(path: str, result: AuditResult) -> None:
    """审计单个 Python 文件（仅读取分析，不执行）。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        result.findings.append(Finding(
            file=path, line=0, rule="文件读取失败",
            severity="低", match="", message=f"无法读取文件: {e}",
        ))
        return
    result.scanned_files += 1
    result.scanned_lines += len(lines)
    for idx, line in enumerate(lines, start=1):
        _check_line(line, idx, path, result)


def audit_dir(path: str, result: AuditResult) -> None:
    """递归审计目录下所有 .py 文件。"""
    if os.path.isfile(path):
        if path.endswith(".py"):
            audit_file(path, result)
        return
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".venv", "venv", "node_modules")]
        for fn in files:
            if fn.endswith(".py"):
                audit_file(os.path.join(root, fn), result)


def run_security_audit(target: str) -> AuditResult:
    """对目标文件/目录执行安全静态扫描。

    Args:
        target: 文件或目录路径

    Returns:
        AuditResult: 含全部发现与统计
    """
    result = AuditResult()
    audit_dir(target, result)
    # 按严重度排序（高→中→低），同级别按文件/行号
    result.findings.sort(key=lambda f: ({"高": 0, "中": 1, "低": 2}.get(f.severity, 3), f.file, f.line))
    return result
