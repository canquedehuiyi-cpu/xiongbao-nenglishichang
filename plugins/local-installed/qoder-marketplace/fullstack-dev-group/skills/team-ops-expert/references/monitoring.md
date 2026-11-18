# 监控告警（Prometheus / Grafana）（从 SKILL.md §四 展开）

本文件覆盖 Prometheus 指标模型、Exporter、PromQL、告警与 Recording 规则、Grafana 面板与
基于 SLO 的多窗口多燃尽告警。配套 `scripts/gen_alert_rules.py`（生成可直接加载的 rules.yml
与 Grafana 面板脚手架）。**铁律：告警要可行动、低噪音、带 Runbook 链接。**

## 1. Prometheus 指标模型

| 类型 | 含义 | 典型用途 |
|------|------|----------|
| **Counter** | 只增计数器 | 请求数、错误数、丢包数 |
| **Gauge** | 可增可减瞬时值 | 内存、连接数、温度、队列长度 |
| **Histogram** | 观测值分桶 | 请求延迟分布（_bucket/_sum/_count） |
| **Summary** | 分位数(客户端算) | 延迟分位（_sum/_count） |

- 命名约定：`<namespace>_<subsystem>_<name>_<unit>`，如 `http_requests_total`、`node_memory_MemAvailable_bytes`。
- 标签（label）用于维度切分，但**基数爆炸**是头号坑：避免把 user_id/request_id 当 label。

## 2. 常用 Exporter

| 目标 | Exporter | 关键指标 |
|------|----------|----------|
| 主机 | node_exporter | CPU/内存/磁盘/网络/文件系统/负载 |
| Nginx | nginx-prometheus-exporter（或 stub_status 转发） | 活跃连接、请求、状态码 |
| MySQL | mysqld_exporter | 连接、QPS、慢查询、复制延迟 |
| Redis | redis_exporter | 内存、命中率、连接、命令 |
| 黑盒 | blackbox_exporter | 探测 HTTP/TCP/DNS 可用性 |
| 进程 | process-exporter | 进程 CPU/内存/句柄 |
| 自定义 | 应用埋点 `/metrics` | 业务指标 |

## 3. PromQL 速查

| 需求 | 示例 |
|------|------|
| 瞬时值 | `node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes` |
| 速率 | `rate(http_requests_total[5m])` |
| 增长量 | `increase(http_requests_total[1h])` |
| 分位 | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` |
| 聚合 | `sum by (instance) (rate(node_cpu_seconds_total[5m]))` |
| 比值 | `sum(rate(http_requests_total{code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` |
| 预测 | `predict_linear(node_filesystem_avail_bytes[6h], 4*3600) < 0` |

## 4. 告警规则（alerting rules）

原则：**可行动 + 低噪音 + 带注释**。每条规则含 `summary`/`description`/`runbook_url`/`severity`。

```yaml
groups:
  - name: node
    rules:
      - alert: HostHighCpuLoad
        expr: 100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
        for: 10m
        labels: { severity: warning }
        annotations:
          summary: "CPU 高负载 {{ $labels.instance }}"
          description: "idle 低于 15% 持续 10m (当前 {{ $value }}%)"
          runbook_url: "http://runbook/ops/cpu-high"
      - alert: HostDiskWillFill
        expr: predict_linear(node_filesystem_avail_bytes[6h], 4*3600) < 0
        for: 10m
        labels: { severity: warning }
        annotations:
          summary: "磁盘 4h 内将满 {{ $labels.instance }} {{ $labels.mountpoint }}"
```

### 4.1 Recording Rules（降采样，提升查询性能）
```yaml
groups:
  - name: recording
    rules:
      - record: job:http_requests:rate5m
        expr: sum by (job)(rate(http_requests_total[5m]))
      - record: job:http_errors:ratio_rate5m
        expr: sum by (job)(rate(http_requests_total{code=~"5.."}[5m]))
            / sum by (job)(rate(http_requests_total[5m]))
```

## 5. 基于 SLO 的多窗口多燃尽告警（MWMB）

避免"单点抖动误报"。用长短两个窗口 + 错误预算燃尽：

```yaml
groups:
  - name: slo
    rules:
      - alert: SLOBurnRateHigh
        expr: |
          (sum(rate(http_requests_total{code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))) > (14.4 * 0.001)
          and
          (sum(rate(http_requests_total{code=~"5.."}[1h])) / sum(rate(http_requests_total[1h]))) > (14.4 * 0.001)
        for: 2m
        labels: { severity: critical }
        annotations:
          summary: "SLO 快速燃烧 (1h 窗口错误率超 14.4×预算)"
```
- 多窗口（短 5m + 长 1h）+ 多燃尽率（快 14.4× / 慢 6× 等）组合，平衡灵敏度与噪音。

## 6. Grafana 面板建议

| 面板 | 数据源/查询 |
|------|-------------|
| 主机总览 | CPU/内存/磁盘/网络(node_exporter) |
| 可用性与错误率 | `job:http_errors:ratio_rate5m` 时序 + 阈值线 |
| 延迟分位 | `histogram_quantile(0.99, ...)` P50/P95/P99 |
| 饱和度 | 连接数、队列、run queue、conntrack 使用率 |
| SLO 仪表 | 错误预算剩余（Gauge + 趋势） |

- 每个面板/告警注明**含义与处置动作**，避免"看图不知怎么办"。

## 7. 告警分级与路由

| 级别 | 定义 | 通知 | 要求 |
|------|------|------|------|
| critical(P1) | 业务中断/资损 | 电话+IM | ≤5min 响应，立即止血 |
| warning(P2) | 趋势恶化/将断 | IM | ≤15min，排期处理 |
| info(P3) | 提示/可观察 | 工单 | 工作时间处理 |

- Alertmanager 路由按 `severity`/`team` 分组、抑制（如主机宕机抑制其上的服务告警）、静默（维护窗）。

## 8. 避坑
- 告警不是日志：只告警"需要人现在做事"的事，其余进面板/日志。
- 标签基数爆炸会让 Prometheus 内存与查询崩溃，严禁高基数 label。
- 告警必须有 runbook 链接，否则迟早变噪音被静默。
- 监控覆盖"RED + USE"，别只监控 CPU 忘了错误率与饱和度。

## 9. 脚本生成
`scripts/gen_alert_rules.py --type node|nginx|mysql|slo --out rules.yml` 输出上述结构化规则；
`--dashboard out.json` 额外生成 Grafana 面板 JSON（含上面建议的查询）。生成后仍需按环境校准阈值。
