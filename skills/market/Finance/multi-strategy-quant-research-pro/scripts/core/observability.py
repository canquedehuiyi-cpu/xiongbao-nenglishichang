# -*- coding: utf-8 -*-
"""可观测性与自诊断层：运行时监控+健康度评估。

六大能力：
1. 请求计数：总请求/成功/失败/按策略分类
2. 耗时统计：平均/最大/P95/P99
3. 缓存命中率：全局缓存+各模块缓存
4. 模块调用统计：各函数/模块调用次数
5. 自诊断报告：健康度评分+问题清单+优化建议
6. 运行时快照：当前状态导出
"""

import time
import json
from collections import defaultdict, deque


class MetricsCollector:
    """指标收集器。"""

    def __init__(self, max_history: int = 1000):
        self.total_requests = 0
        self.success_requests = 0
        self.failed_requests = 0
        self.strategy_counts = defaultdict(int)
        self.module_counts = defaultdict(int)
        self.latencies = deque(maxlen=max_history)
        self.error_types = defaultdict(int)
        self.start_time = time.time()

    def record_request(self, strategy: str = "", success: bool = True,
                       latency: float = 0, error_type: str = "", module: str = ""):
        """记录一次请求。"""
        self.total_requests += 1
        if success:
            self.success_requests += 1
        else:
            self.failed_requests += 1
            if error_type:
                self.error_types[error_type] += 1
        if strategy:
            self.strategy_counts[strategy] += 1
        if module:
            self.module_counts[module] += 1
        if latency > 0:
            self.latencies.append(latency)

    def record_module_call(self, module: str):
        """记录模块调用。"""
        self.module_counts[module] += 1

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 100.0
        return round(self.success_requests / self.total_requests * 100, 1)

    @property
    def avg_latency(self) -> float:
        if not self.latencies:
            return 0
        return round(sum(self.latencies) / len(self.latencies), 3)

    @property
    def max_latency(self) -> float:
        if not self.latencies:
            return 0
        return round(max(self.latencies), 3)

    @property
    def p95_latency(self) -> float:
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return round(sorted_lat[min(idx, len(sorted_lat) - 1)], 3)

    @property
    def p99_latency(self) -> float:
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.99)
        return round(sorted_lat[min(idx, len(sorted_lat) - 1)], 3)

    @property
    def uptime(self) -> float:
        return round(time.time() - self.start_time, 1)

    def snapshot(self) -> dict:
        """导出当前状态快照。"""
        return {
            "total_requests": self.total_requests,
            "success_requests": self.success_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate,
            "avg_latency": self.avg_latency,
            "max_latency": self.max_latency,
            "p95_latency": self.p95_latency,
            "p99_latency": self.p99_latency,
            "uptime_seconds": self.uptime,
            "strategy_counts": dict(self.strategy_counts),
            "top_modules": dict(sorted(self.module_counts.items(),
                                       key=lambda x: -x[1])[:10]),
            "error_types": dict(self.error_types),
        }


class CacheMonitor:
    """缓存监控。"""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.hits_by_cache = {}
        self.misses_by_cache = {}
        self.cache_sizes = {}

    def record_hit(self, cache_name: str = "default"):
        self.hits += 1
        self.hits_by_cache[cache_name] = self.hits_by_cache.get(cache_name, 0) + 1

    def record_miss(self, cache_name: str = "default"):
        self.misses += 1
        self.misses_by_cache[cache_name] = self.misses_by_cache.get(cache_name, 0) + 1

    def update_size(self, cache_name: str, size: int):
        self.cache_sizes[cache_name] = size

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return round(self.hits / total * 100, 1) if total > 0 else 0

    def snapshot(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "hits_by_cache": self.hits_by_cache,
            "misses_by_cache": self.misses_by_cache,
            "cache_sizes": self.cache_sizes,
        }


class SelfDiagnostic:
    """自诊断引擎：健康度评分+问题清单+优化建议。"""

    def __init__(self, metrics: MetricsCollector, cache_monitor: CacheMonitor):
        self.metrics = metrics
        self.cache_monitor = cache_monitor

    def diagnose(self) -> dict:
        """执行自诊断，返回健康度报告。"""
        issues = []
        score = 100

        # 1. 成功率检查
        if self.metrics.total_requests > 10:
            if self.metrics.success_rate < 90:
                issues.append({
                    "severity": "high",
                    "category": "reliability",
                    "issue": f"成功率过低（{self.metrics.success_rate}%）",
                    "suggestion": "检查数据源稳定性，启用降级方案",
                })
                score -= 20
            elif self.metrics.success_rate < 95:
                issues.append({
                    "severity": "medium",
                    "category": "reliability",
                    "issue": f"成功率偏低（{self.metrics.success_rate}%）",
                    "suggestion": "关注失败请求，优化重试机制",
                })
                score -= 10

        # 2. 延迟检查
        if self.metrics.avg_latency > 5:
            issues.append({
                "severity": "high",
                "category": "performance",
                "issue": f"平均延迟过高（{self.metrics.avg_latency}s）",
                "suggestion": "启用缓存，优化数据获取，考虑异步处理",
            })
            score -= 15
        elif self.metrics.avg_latency > 2:
            issues.append({
                "severity": "medium",
                "category": "performance",
                "issue": f"平均延迟偏高（{self.metrics.avg_latency}s）",
                "suggestion": "检查慢查询，增加预计算",
            })
            score -= 8

        if self.metrics.p95_latency > 10:
            issues.append({
                "severity": "medium",
                "category": "performance",
                "issue": f"P95延迟过高（{self.metrics.p95_latency}s）",
                "suggestion": "优化长尾请求，增加超时降级",
            })
            score -= 5

        # 3. 缓存命中率检查
        if self.cache_monitor.hits + self.cache_monitor.misses > 10:
            if self.cache_monitor.hit_rate < 30:
                issues.append({
                    "severity": "low",
                    "category": "performance",
                    "issue": f"缓存命中率低（{self.cache_monitor.hit_rate}%）",
                    "suggestion": "增加缓存覆盖，调整缓存键设计",
                })
                score -= 5

        # 4. 错误类型分析
        if self.metrics.error_types:
            top_error = max(self.metrics.error_types.items(), key=lambda x: x[1])
            if top_error[1] > self.metrics.total_requests * 0.1:
                issues.append({
                    "severity": "medium",
                    "category": "reliability",
                    "issue": f"高频错误类型：{top_error[0]}（{top_error[1]}次）",
                    "suggestion": "针对该错误类型增加专项处理",
                })
                score -= 8

        # 5. 运行时长检查
        if self.metrics.uptime > 3600 and self.metrics.total_requests == 0:
            issues.append({
                "severity": "low",
                "category": "usage",
                "issue": "运行超过1小时但无请求",
                "suggestion": "确认skill是否正常被调用",
            })
            score -= 3

        score = max(0, score)

        # 健康等级
        if score >= 90:
            level = "优秀"
        elif score >= 75:
            level = "良好"
        elif score >= 60:
            level = "一般"
        else:
            level = "需关注"

        return {
            "health_score": score,
            "health_level": level,
            "issue_count": len(issues),
            "issues": issues,
            "summary": f"健康度{score}/100（{level}），发现{len(issues)}个问题" if issues else f"健康度{score}/100（{level}），运行状态良好",
        }

    def generate_report(self) -> str:
        """生成可读的自诊断报告。"""
        diag = self.diagnose()
        snap = self.metrics.snapshot()
        cache_snap = self.cache_monitor.snapshot()

        lines = [
            "=" * 50,
            "量化研究 Skill 自诊断报告",
            "=" * 50,
            f"健康度: {diag['health_score']}/100（{diag['health_level']}）",
            f"运行时长: {snap['uptime_seconds']}秒",
            "",
            "【请求统计】",
            f"  总请求: {snap['total_requests']}",
            f"  成功: {snap['success_requests']} / 失败: {snap['failed_requests']}",
            f"  成功率: {snap['success_rate']}%",
            "",
            "【延迟统计】",
            f"  平均: {snap['avg_latency']}s",
            f"  P95: {snap['p95_latency']}s / P99: {snap['p99_latency']}s",
            f"  最大: {snap['max_latency']}s",
            "",
            "【缓存统计】",
            f"  命中: {cache_snap['hits']} / 未命中: {cache_snap['misses']}",
            f"  命中率: {cache_snap['hit_rate']}%",
            "",
        ]

        if snap["strategy_counts"]:
            lines.append("【策略使用分布】")
            for s, c in sorted(snap["strategy_counts"].items(), key=lambda x: -x[1])[:5]:
                lines.append(f"  {s}: {c}次")
            lines.append("")

        if diag["issues"]:
            lines.append("【发现问题】")
            for i, issue in enumerate(diag["issues"], 1):
                lines.append(f"  {i}. [{issue['severity']}] {issue['issue']}")
                lines.append(f"     建议: {issue['suggestion']}")
        else:
            lines.append("【发现问题】无")

        lines.append("=" * 50)
        return "\n".join(lines)


class ObservabilityHub:
    """可观测性中心：整合所有监控。"""

    def __init__(self):
        self.metrics = MetricsCollector()
        self.cache_monitor = CacheMonitor()
        self.diagnostic = SelfDiagnostic(self.metrics, self.cache_monitor)
        self.custom_metrics = defaultdict(float)

    def record(self, strategy: str = "", success: bool = True,
               latency: float = 0, error_type: str = "", module: str = ""):
        """记录一次请求。"""
        self.metrics.record_request(strategy, success, latency, error_type, module)

    def cache_hit(self, name: str = "default"):
        self.cache_monitor.record_hit(name)

    def cache_miss(self, name: str = "default"):
        self.cache_monitor.record_miss(name)

    def custom(self, name: str, value: float = 1):
        """记录自定义指标。"""
        self.custom_metrics[name] += value

    def health_check(self) -> dict:
        """快速健康检查。"""
        return {
            "healthy": self.metrics.success_rate >= 90 or self.metrics.total_requests < 10,
            "score": self.diagnostic.diagnose()["health_score"],
            "requests": self.metrics.total_requests,
            "avg_latency": self.metrics.avg_latency,
        }

    def full_report(self) -> str:
        """完整诊断报告。"""
        return self.diagnostic.generate_report()

    def export_json(self) -> str:
        """导出JSON格式的监控数据。"""
        return json.dumps({
            "metrics": self.metrics.snapshot(),
            "cache": self.cache_monitor.snapshot(),
            "diagnostic": self.diagnostic.diagnose(),
            "custom": dict(self.custom_metrics),
        }, ensure_ascii=False, indent=2)


# 全局实例
_global_hub = ObservabilityHub()


def get_observability() -> ObservabilityHub:
    """获取全局可观测性中心。"""
    return _global_hub
