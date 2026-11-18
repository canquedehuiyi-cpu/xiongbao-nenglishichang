# -*- coding: utf-8 -*-
"""核心运行时支撑模块。

三部分：
- ResponseEngine: 按用户熟练度分层组织回答口径与详略程度
- 韧性容错: 熔断、数据源降级、超时兜底、退避重试、错误分类与统一管理
- 可观测性: 指标采集、缓存监控、自诊断与统一观测入口

全部为确定性的本地逻辑，不依赖任何第三方库。
"""

from .response_engine import ResponseEngine, detect_user_level
from .resilience import (
    CircuitBreaker,
    CircuitBreakerOpen,
    DataSourceFallback,
    DataSourceError,
    PartialOutput,
    TimeoutFallback,
    RetryWithBackoff,
    ErrorClassifier,
    ResilienceManager,
)
from .observability import (
    MetricsCollector,
    CacheMonitor,
    SelfDiagnostic,
    ObservabilityHub,
    get_observability,
)

__all__ = [
    "ResponseEngine",
    "detect_user_level",
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "DataSourceFallback",
    "DataSourceError",
    "PartialOutput",
    "TimeoutFallback",
    "RetryWithBackoff",
    "ErrorClassifier",
    "ResilienceManager",
    "MetricsCollector",
    "CacheMonitor",
    "SelfDiagnostic",
    "ObservabilityHub",
    "get_observability",
]
