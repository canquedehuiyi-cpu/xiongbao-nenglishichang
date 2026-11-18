"""交易系统代码审计包。

模块：
- security.py     静态安全扫描（API密钥泄露/危险函数/SQL注入等）
- concurrency.py  并发安全审计（多线程止损失效/竞态 + asyncio 阻塞/取消/一致性）
"""

from .security import run_security_audit, AuditResult, Finding
from .concurrency import audit_dir_for_concurrency, audit_file_for_concurrency

__all__ = [
    "run_security_audit",
    "audit_dir_for_concurrency",
    "audit_file_for_concurrency",
    "AuditResult",
    "Finding",
]
