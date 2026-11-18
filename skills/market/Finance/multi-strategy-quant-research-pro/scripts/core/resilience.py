# -*- coding: utf-8 -*-
"""错误自愈与降级层：保障skill在异常情况下仍能输出可用结果。

六大机制：
1. 数据源切换：主数据源失败自动切换备用
2. 部分输出：部分股票失败时输出已成功的，标注缺失
3. 超时降级：超时后用缓存或简化策略
4. 熔断机制：连续失败后暂停请求，避免雪崩
5. 重试机制：指数退避重试
6. 错误分类：网络/数据/参数/未知，分别处理
"""

import time
from typing import Callable, Optional, Any


class CircuitBreaker:
    """熔断器：连续失败后暂停请求。

    三态：closed（正常）-> open（熔断）-> half_open（半开试探）
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed / open / half_open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """执行函数，带熔断保护。"""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
            else:
                raise CircuitBreakerOpen(
                    f"熔断器已打开，剩余{self.recovery_timeout - int(time.time() - self.last_failure_time)}秒"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    @property
    def is_open(self) -> bool:
        return self.state == "open"

    def reset(self):
        self.failure_count = 0
        self.state = "closed"

    def stats(self) -> dict:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "threshold": self.failure_threshold,
        }


class CircuitBreakerOpen(Exception):
    """熔断器打开异常。"""
    pass


class DataSourceFallback:
    """数据源切换：主数据源失败自动切换备用。"""

    def __init__(self):
        self.sources = []  # [(name, func, priority)]
        self.fallback_log = []

    def register(self, name: str, func: Callable, priority: int = 0):
        """注册数据源。"""
        self.sources.append((name, func, priority))
        self.sources.sort(key=lambda x: x[2])

    def fetch(self, *args, **kwargs) -> tuple[Any, str]:
        """按优先级依次尝试数据源。

        Returns:
            (data, source_name)
        """
        errors = []
        for name, func, _ in self.sources:
            try:
                data = func(*args, **kwargs)
                if data:
                    self.fallback_log.append({"success": name, "tried": [e[0] for e in errors]})
                    return data, name
            except Exception as e:
                errors.append((name, str(e)))
                continue

        raise DataSourceError(f"所有数据源均失败: {errors}")

    def stats(self) -> dict:
        return {
            "registered_sources": len(self.sources),
            "fallback_count": len(self.fallback_log),
            "recent_fallbacks": self.fallback_log[-5:],
        }


class DataSourceError(Exception):
    """所有数据源均失败。"""
    pass


class PartialOutput:
    """部分输出：部分失败时输出已成功的，标注缺失。"""

    def __init__(self):
        self.success = []
        self.failed = []

    def add_success(self, item: Any):
        self.success.append(item)

    def add_failed(self, identifier: str, reason: str):
        self.failed.append({"id": identifier, "reason": reason})

    def result(self, min_success: int = 1) -> dict:
        """生成部分输出结果。

        Args:
            min_success: 最少成功数，低于此数视为整体失败

        Returns:
            dict: {success_count, failed_count, data, missing, usable, note}
        """
        usable = len(self.success) >= min_success
        return {
            "success_count": len(self.success),
            "failed_count": len(self.failed),
            "data": self.success,
            "missing": self.failed,
            "usable": usable,
            "note": (f"成功{len(self.success)}只，失败{len(self.failed)}只"
                     if self.failed else f"全部成功（{len(self.success)}只）"),
        }


class TimeoutFallback:
    """超时降级。

    说明：本方法为同步调用，无法在到达 timeout 时强制中断正在执行的 func；
    timeout 仅在 func 返回后用于判定耗时是否超限（超限标注为 fresh_slow）。
    真正的降级发生在 func 抛出异常时：优先回退缓存，其次使用简化策略。
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.cache = {}
        self.fallback_count = 0

    def call_with_cache(self, key: str, func: Callable, *args, **kwargs) -> tuple[Any, str]:
        """带缓存降级的同步调用（不会在超时点中断 func，详见类说明）。

        Returns:
            (result, source)  source: "fresh"/"fresh_slow"/"cache"/"simplified"
        """
        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            if elapsed <= self.timeout:
                self.cache[key] = result
                return result, "fresh"
            # 超时但有结果，仍返回但标注
            return result, "fresh_slow"
        except Exception:
            # 失败时尝试缓存
            if key in self.cache:
                self.fallback_count += 1
                return self.cache[key], "cache"
            # 无缓存，尝试简化策略
            simplified = self._simplified_fallback(*args, **kwargs)
            if simplified is not None:
                self.fallback_count += 1
                return simplified, "simplified"
            raise

    def _simplified_fallback(self, *args, **kwargs) -> Optional[Any]:
        """简化策略降级（子类可重写）。"""
        return None

    def stats(self) -> dict:
        return {
            "timeout": self.timeout,
            "cache_size": len(self.cache),
            "fallback_count": self.fallback_count,
        }


class RetryWithBackoff:
    """指数退避重试。"""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 10.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """带重试的调用。"""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    time.sleep(delay)
        raise last_error


class ErrorClassifier:
    """错误分类与恢复建议。"""

    @staticmethod
    def classify(error: Exception) -> dict:
        """分类错误并给出恢复建议。"""
        msg = str(error).lower()

        if any(kw in msg for kw in ["timeout", "timed out", "连接超时", "超时"]):
            return {
                "type": "network_timeout",
                "severity": "medium",
                "recoverable": True,
                "action": "重试或切换备用数据源",
                "user_message": "数据获取超时，正在尝试备用通道...",
            }
        elif any(kw in msg for kw in ["connection", "连接", "网络", "network", "dns"]):
            return {
                "type": "network_error",
                "severity": "high",
                "recoverable": True,
                "action": "检查网络连接，切换数据源",
                "user_message": "网络连接异常，已切换备用数据源",
            }
        elif any(kw in msg for kw in ["404", "not found", "不存在", "无数据"]):
            return {
                "type": "data_not_found",
                "severity": "low",
                "recoverable": False,
                "action": "跳过该股票，继续处理其他股票",
                "user_message": "部分股票数据缺失，已跳过并标注",
            }
        elif any(kw in msg for kw in ["429", "rate limit", "限流", "频繁"]):
            return {
                "type": "rate_limited",
                "severity": "medium",
                "recoverable": True,
                "action": "降低请求频率，使用缓存",
                "user_message": "请求过于频繁，已自动降速并使用缓存",
            }
        elif any(kw in msg for kw in ["参数", "invalid", "参数错误", "value error"]):
            return {
                "type": "parameter_error",
                "severity": "low",
                "recoverable": False,
                "action": "检查并修正参数",
                "user_message": "参数有误，请检查筛选条件",
            }
        else:
            return {
                "type": "unknown",
                "severity": "medium",
                "recoverable": True,
                "action": "记录日志，尝试降级方案",
                "user_message": "遇到未知问题，已启用降级方案",
            }


class ResilienceManager:
    """自愈管理器：整合所有机制。"""

    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self.data_source = DataSourceFallback()
        self.partial_output = PartialOutput()
        self.timeout_fallback = TimeoutFallback()
        self.retry = RetryWithBackoff()
        self.error_log = []

    def safe_execute(self, func: Callable, *args,
                     error_context: str = "", **kwargs) -> dict:
        """安全执行：整合熔断+重试+错误分类+部分输出。

        Returns:
            dict: {success, result, error, recovery_action, user_message}
        """
        try:
            # 熔断检查
            if self.circuit_breaker.is_open:
                return {
                    "success": False,
                    "result": None,
                    "error": "circuit_open",
                    "recovery_action": "等待熔断恢复",
                    "user_message": "系统繁忙，请稍后再试",
                }

            # 带重试执行
            result = self.retry.call(
                self.circuit_breaker.call, func, *args, **kwargs
            )
            return {
                "success": True,
                "result": result,
                "error": None,
                "recovery_action": None,
                "user_message": None,
            }
        except Exception as e:
            # 错误分类
            classification = ErrorClassifier.classify(e)
            self.error_log.append({
                "context": error_context,
                "error": str(e),
                "classification": classification,
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

            return {
                "success": False,
                "result": None,
                "error": str(e),
                "classification": classification,
                "recovery_action": classification["action"],
                "user_message": classification["user_message"],
            }

    def stats(self) -> dict:
        return {
            "circuit_breaker": self.circuit_breaker.stats(),
            "data_source": self.data_source.stats(),
            "timeout_fallback": self.timeout_fallback.stats(),
            "error_count": len(self.error_log),
            "recent_errors": self.error_log[-5:],
        }
