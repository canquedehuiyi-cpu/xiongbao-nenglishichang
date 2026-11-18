# -*- coding: utf-8 -*-
"""工具层：性能优化与通用工具。

- SmartCache: 智能缓存（TTL + LRU + 内存/文件双层）
- PerformanceMonitor: 性能监控（耗时统计 + 命中率）
- cached: 函数级缓存装饰器
- batch_precompute: 批量预计算
- vectorized_map / vectorized_filter: 向量化操作
- chunked_process: 分块处理
- precompute_indicators: 指标预计算
"""

from .performance import (
    SmartCache,
    PerformanceMonitor,
    get_global_cache,
    cached,
    batch_precompute,
    vectorized_map,
    vectorized_filter,
    chunked_process,
    precompute_indicators,
)

__all__ = [
    "SmartCache",
    "PerformanceMonitor",
    "get_global_cache",
    "cached",
    "batch_precompute",
    "vectorized_map",
    "vectorized_filter",
    "chunked_process",
    "precompute_indicators",
]
