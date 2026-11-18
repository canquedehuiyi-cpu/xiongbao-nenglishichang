# -*- coding: utf-8 -*-
"""性能优化层：智能缓存+预计算+向量化工具。

三大优化：
1. 智能缓存：TTL过期+LRU淘汰的内存缓存
2. 预计算指标：批量计算MA/MACD/RSI，避免重复
3. 向量化工具：列表推导式、批量操作
"""

import time
import hashlib
from collections import OrderedDict
from typing import Any, Callable, Optional


class SmartCache:
    """智能缓存：TTL过期 + LRU淘汰。

    用法：
        cache = SmartCache(max_size=500, ttl=300)
        cache.set("key", value)
        value = cache.get("key")
    """

    def __init__(self, max_size: int = 500, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self._cache = OrderedDict()
        self._expiry = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            if time.time() < self._expiry.get(key, 0):
                self._cache.move_to_end(key)
                self.hits += 1
                return self._cache[key]
            else:
                del self._cache[key]
                self._expiry.pop(key, None)
        self.misses += 1
        return None

    def set(self, key: str, value: Any, ttl: int = None):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        self._expiry[key] = time.time() + (ttl or self.ttl)
        # LRU淘汰
        while len(self._cache) > self.max_size:
            old_key, _ = self._cache.popitem(last=False)
            self._expiry.pop(old_key, None)

    def clear(self):
        self._cache.clear()
        self._expiry.clear()
        self.hits = 0
        self.misses = 0

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return round(self.hits / total * 100, 1) if total > 0 else 0

    def stats(self) -> dict:
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
        }


# 全局缓存实例
_global_cache = SmartCache(max_size=1000, ttl=600)


def cached(key_prefix: str, ttl: int = 300):
    """缓存装饰器。

    用法：
        @cached("kline_", ttl=300)
        def get_kline(code):
            ...
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            key = key_prefix + hashlib.md5(
                str(args).encode() + str(sorted(kwargs.items())).encode()
            ).hexdigest()[:16]
            cached_val = _global_cache.get(key)
            if cached_val is not None:
                return cached_val
            result = func(*args, **kwargs)
            if result is not None:
                _global_cache.set(key, result, ttl)
            return result
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


def precompute_indicators(klines: list[dict]) -> dict:
    """预计算常用技术指标，一次计算多次使用。

    预计算：MA5/10/20/60, MACD, RSI14, 布林带, ATR14

    Args:
        klines: K线列表

    Returns:
        dict: {ma5, ma10, ma20, ma60, macd, rsi, boll, atr}
    """
    from indicators.technical import calc_ma, calc_macd, calc_rsi, calc_bollinger, calc_atr

    return {
        "ma5": calc_ma(klines, 5),
        "ma10": calc_ma(klines, 10),
        "ma20": calc_ma(klines, 20),
        "ma60": calc_ma(klines, 60),
        "macd": calc_macd(klines),
        "rsi": calc_rsi(klines, 14),
        "boll": calc_bollinger(klines, 20, 2),
        "atr": calc_atr(klines, 14),
    }


def batch_precompute(stocks: list[dict]) -> dict:
    """批量预计算多只股票的指标。

    Args:
        stocks: 股票列表，每项含code和klines

    Returns:
        dict: {code: indicators}
    """
    result = {}
    for s in stocks:
        code = s.get("code", "")
        klines = s.get("klines", [])
        if klines:
            result[code] = precompute_indicators(klines)
    return result


def vectorized_filter(data: list[dict], condition: Callable) -> list[dict]:
    """向量化过滤：用列表推导式替代循环。

    Args:
        data: 数据列表
        condition: 过滤条件函数

    Returns:
        list: 过滤后的数据
    """
    return [item for item in data if condition(item)]


def vectorized_map(data: list[dict], transform: Callable) -> list:
    """向量化映射。

    Args:
        data: 数据列表
        transform: 转换函数

    Returns:
        list: 转换后的数据
    """
    return [transform(item) for item in data]


def chunked_process(data: list, chunk_size: int = 50,
                    processor: Callable = None) -> list:
    """分块处理：避免一次性处理大量数据导致内存峰值。

    Args:
        data: 数据列表
        chunk_size: 每块大小
        processor: 处理函数

    Returns:
        list: 处理结果
    """
    if processor is None:
        return data
    result = []
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        result.extend(processor(chunk))
    return result


class PerformanceMonitor:
    """性能监控：记录各模块耗时。

    用法：
        monitor = PerformanceMonitor()
        with monitor.timer("fetch_data"):
            fetch_data()
        print(monitor.report())
    """

    def __init__(self):
        self.timings = {}
        self.counts = {}

    def timer(self, name: str):
        class _Timer:
            def __enter__(self_inner):
                self_inner.start = time.time()
                return self_inner
            def __exit__(self_inner, *args):
                elapsed = time.time() - self_inner.start
                self.timings[name] = self.timings.get(name, 0) + elapsed
                self.counts[name] = self.counts.get(name, 0) + 1
        return _Timer()

    def report(self) -> dict:
        total = sum(self.timings.values())
        return {
            "total_time": round(total, 3),
            "modules": {
                name: {
                    "total_time": round(t, 3),
                    "calls": self.counts.get(name, 0),
                    "avg_time": round(t / self.counts.get(name, 1), 4),
                    "pct": round(t / total * 100, 1) if total > 0 else 0,
                }
                for name, t in sorted(self.timings.items(), key=lambda x: -x[1])
            },
            "cache_stats": _global_cache.stats(),
        }


def get_global_cache() -> SmartCache:
    """获取全局缓存实例。"""
    return _global_cache
