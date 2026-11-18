#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_alert_rules.py — 生成 Prometheus 告警/Recording 规则与 Grafana 面板脚手架

仅依赖 Python 标准库。适用 WorkBuddy ops-expert skill (references/monitoring.md)。

用法示例:
  python3 gen_alert_rules.py --type node --out rules.yml
  python3 gen_alert_rules.py --type node,nginx,mysql,slo --out rules.yml --dashboard dash.json --job myapp
  python3 gen_alert_rules.py --type slo --out slo.rules.yml --error-budget 0.001 --window-fast 5m

输出:
  - rules.yml : 可直接被 Prometheus rule_files 加载的 groups
  - dash.json : Grafana dashboard 脚手架(需手动导入并按数据源调整)
"""
import argparse
import json
import sys


def yq(s, lvl=0):
    """极简 YAML 引号处理：仅在含特殊字符时加单引号。"""
    s = str(s)
    if s == "" or any(c in s for c in [":", "#", "{", "}", "[", "]", ",", "&", "*", "?", "|", ">", "'", '"']):
        return "'" + s.replace("'", "''") + "'"
    return s


def emit_rule(f, rule, indent=4):
    sp = " " * indent
    sp2 = " " * (indent + 2)
    if "record" in rule:
        f.write(f"{sp}- record: {yq(rule['record'])}\n")
    else:
        f.write(f"{sp}- alert: {yq(rule['alert'])}\n")
    expr = rule["expr"]
    # 多行 expr 用 '|' 块
    if "\n" in expr:
        f.write(f"{sp2}expr: |\n")
        for line in expr.split("\n"):
            f.write(f"{sp2}  {line}\n")
    else:
        f.write(f"{sp2}expr: {yq(expr)}\n")
    if "for" in rule:
        f.write(f"{sp2}for: {rule['for']}\n")
    if rule.get("labels"):
        f.write(f"{sp2}labels:\n")
        for k, v in rule["labels"].items():
            f.write(f"{sp2}  {k}: {yq(v)}\n")
    if rule.get("annotations"):
        f.write(f"{sp2}annotations:\n")
        for k, v in rule["annotations"].items():
            f.write(f"{sp2}  {k}: {yq(v)}\n")


def node_rules(job="node"):
    return [
        {"alert": "HostDown", "expr": f"up{{job=~\"{job}\"}} == 0", "for": "1m",
         "labels": {"severity": "critical"},
         "annotations": {"summary": "节点 {{ $labels.instance }} 失联",
                         "description": "up 指标为 0 超过 1m", "runbook_url": "http://runbook/ops/host-down"}},
        {"alert": "HostHighCpuLoad",
         "expr": "100 - (avg by(instance)(rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100) > 85",
         "for": "10m", "labels": {"severity": "warning"},
         "annotations": {"summary": "CPU 高负载 {{ $labels.instance }}",
                         "description": "idle 低于 15% 持续 10m (当前 {{ $value }}%)",
                         "runbook_url": "http://runbook/ops/cpu-high"}},
        {"alert": "HostMemoryLow",
         "expr": "(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100 > 90",
         "for": "5m", "labels": {"severity": "warning"},
         "annotations": {"summary": "内存不足 {{ $labels.instance }}", "description": "已用 > 90% ({{ $value }}%)"}},
        {"alert": "HostDiskWillFill",
         "expr": "predict_linear(node_filesystem_avail_bytes[6h], 4*3600) < 0",
         "for": "10m", "labels": {"severity": "warning"},
         "annotations": {"summary": "磁盘 4h 内将满 {{ $labels.instance }} {{ $labels.mountpoint }}",
                         "description": "按 6h 趋势推算 4h 后可用空间 < 0"}},
        {"alert": "HostDiskSpaceHigh",
         "expr": "100 - (node_filesystem_avail_bytes / node_filesystem_size_bytes * 100) > 85",
         "for": "5m", "labels": {"severity": "warning"},
         "annotations": {"summary": "磁盘使用率高 {{ $labels.instance }} {{ $labels.mountpoint }}",
                         "description": "使用率 > 85% ({{ $value }}%)"}},
        {"alert": "HostInodeExhaustion",
         "expr": "node_filesystem_files_free / node_filesystem_files * 100 < 10",
         "for": "5m", "labels": {"severity": "warning"},
         "annotations": {"summary": "inode 即将耗尽 {{ $labels.instance }}", "description": "可用 inode < 10%"}},
        {"alert": "HostHighLoad",
         "expr": "node_load5 / count by(instance)(node_cpu_seconds_total{mode=\"idle\"}) > 2",
         "for": "10m", "labels": {"severity": "warning"},
         "annotations": {"summary": "负载偏高 {{ $labels.instance }}", "description": "load5/核数 > 2"}},
        {"alert": "HostNetworkErrors",
         "expr": "rate(node_network_receive_errs_total[5m]) > 0 or rate(node_network_transmit_errs_total[5m]) > 0",
         "for": "5m", "labels": {"severity": "warning"},
         "annotations": {"summary": "网卡错误 {{ $labels.instance }} {{ $labels.device }}"}},
        {"alert": "HostFilesystemReadOnly",
         "expr": "node_filesystem_readonly == 1", "for": "1m",
         "labels": {"severity": "critical"},
         "annotations": {"summary": "文件系统只读 {{ $labels.instance }} {{ $labels.mountpoint }}"}},
    ]


def nginx_rules(job="nginx"):
    return [
        {"alert": "NginxUpstreamDown",
         "expr": f"nginx_upstream_server_up{{job=~\"{job}\"}} == 0", "for": "1m",
         "labels": {"severity": "critical"},
         "annotations": {"summary": "上游下线 {{ $labels.upstream }} / {{ $labels.server }}",
                         "runbook_url": "http://runbook/ops/nginx-upstream-down"}},
        {"alert": "NginxHigh5xxRatio",
         "expr": "sum(rate(nginx_http_requests_total{status=~\"5..\"}[5m])) / sum(rate(nginx_http_requests_total[5m])) > 0.02",
         "for": "5m", "labels": {"severity": "warning"},
         "annotations": {"summary": "5xx 比例过高 ({{ $value }})", "description": "5xx/总请求 > 2% 持续 5m"}},
        {"alert": "NginxRequestDrop",
         "expr": "sum(rate(nginx_http_requests_total[5m])) == 0", "for": "5m",
         "labels": {"severity": "warning"},
         "annotations": {"summary": "Nginx 请求量跌为 0，可能已停止接收"}},
    ]


def mysql_rules(job="mysql"):
    return [
        {"alert": "MySQLDown", "expr": f"mysql_up{{job=~\"{job}\"}} == 0", "for": "1m",
         "labels": {"severity": "critical"},
         "annotations": {"summary": "MySQL 不可达 {{ $labels.instance }}"}},
        {"alert": "MySQLSlaveLag",
         "expr": "mysql_slave_status_seconds_behind_master > 30", "for": "5m",
         "labels": {"severity": "warning"},
         "annotations": {"summary": "主从延迟 {{ $labels.instance }} = {{ $value }}s"}},
        {"alert": "MySQLTooManyConnections",
         "expr": "mysql_global_status_threads_connected / mysql_global_variables_max_connections * 100 > 85",
         "for": "5m", "labels": {"severity": "warning"},
         "annotations": {"summary": "连接数接近上限 {{ $labels.instance }} ({{ $value }}%)"}},
        {"alert": "MySQLSlowQueriesSpike",
         "expr": "rate(mysql_global_status_slow_queries[5m]) > 0", "for": "10m",
         "labels": {"severity": "warning"},
         "annotations": {"summary": "慢查询增多 {{ $labels.instance }}"}},
    ]


def slo_rules(metric="http_requests_total", code_label="code", budget=0.001,
              w_fast="5m", w_slow="1h"):
    # 多窗口多燃尽(MWMB): 快窗口 14.4x 预算, 慢窗口 6x 预算(此处给快窗, 另可加慢窗)
    err = f'sum(rate({metric}{{{code_label}=~"5.."}}[{w_fast}])) / sum(rate({metric}[{w_fast}]))'
    err_slow = f'sum(rate({metric}{{{code_label}=~"5.."}}[{w_slow}])) / sum(rate({metric}[{w_slow}]))'
    burn_fast = 14.4 * budget
    burn_slow = 6 * budget
    expr = f"({err}) > {burn_fast}\n  and\n({err_slow}) > {burn_slow}"
    return [
        {"alert": "SLOBurnRateHigh", "expr": expr, "for": "2m",
         "labels": {"severity": "critical"},
         "annotations": {"summary": "SLO 快速燃烧 (错误预算消耗过快)",
                         "description": f"快窗 {w_fast} 超 {burn_fast:.4f} 且慢窗 {w_slow} 超 {burn_slow:.4f} 预算",
                         "runbook_url": "http://runbook/slo/burn-rate"}},
        # Recording rule 放在 groups 里单独返回
    ]


def recording_rules(metric="http_requests_total", code_label="code"):
    return [
        {"record": "job:http_requests:rate5m",
         "expr": f"sum by (job)(rate({metric}[5m]))"},
        {"record": "job:http_errors:ratio_rate5m",
         "expr": f"sum by (job)(rate({metric}{{{code_label}=~\"5..\"}}[5m])) / sum by (job)(rate({metric}[5m]))"},
    ]


def build_groups(types, args):
    groups = []
    if "node" in types:
        groups.append({"name": "node-alerts", "rules": node_rules(args.job)})
    if "nginx" in types:
        groups.append({"name": "nginx-alerts", "rules": nginx_rules(args.job)})
    if "mysql" in types:
        groups.append({"name": "mysql-alerts", "rules": mysql_rules(args.job)})
    if "slo" in types:
        groups.append({"name": "slo-alerts", "rules": slo_rules(args.slo_metric, args.slo_code,
                                                                  args.error_budget, args.w_fast, args.w_slow)})
    # recording 规则始终附带(若选了 slo 或 all)
    if "slo" in types or "all" in types:
        groups.append({"name": "recording", "rules": recording_rules(args.slo_metric, args.slo_code)})
    return groups


def write_rules(path, groups):
    with open(path, "w", encoding="utf-8") as f:
        f.write("# 由 ops-expert gen_alert_rules.py 生成 — 按环境校准阈值\n")
        f.write("groups:\n")
        for g in groups:
            f.write(f"- name: {g['name']}\n  rules:\n")
            for r in g["rules"]:
                emit_rule(f, r, indent=2)
    print(f"已生成规则: {path} (groups={len(groups)})")


def build_dashboard(types, args):
    panels = []
    pid = 1
    if "node" in types:
        panels += [
            {"id": pid, "title": "CPU 使用率 %", "type": "timeseries",
             "targets": [{"expr": "100 - (avg by(instance)(rate(node_cpu_seconds_total{mode=\"idle\"}[5m]))*100)", "legendFormat": "{{instance}}"}]},
            {"id": (pid := pid + 1), "title": "内存使用率 %", "type": "timeseries",
             "targets": [{"expr": "(1 - node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes)*100", "legendFormat": "{{instance}}"}]},
            {"id": (pid := pid + 1), "title": "磁盘使用率 %", "type": "timeseries",
             "targets": [{"expr": "100 - (node_filesystem_avail_bytes/node_filesystem_size_bytes*100)", "legendFormat": "{{instance}} {{mountpoint}}"}]},
            {"id": (pid := pid + 1), "title": "网络吞吐", "type": "timeseries",
             "targets": [{"expr": "rate(node_network_receive_bytes_total[5m])", "legendFormat": "rx {{device}}"},
                          {"expr": "rate(node_network_transmit_bytes_total[5m])", "legendFormat": "tx {{device}}"}]},
        ]
    if "nginx" in types:
        panels.append({"id": (pid := pid + 1), "title": "Nginx 5xx 比例", "type": "timeseries",
                       "targets": [{"expr": "sum(rate(nginx_http_requests_total{status=~\"5..\"}[5m]))/sum(rate(nginx_http_requests_total[5m]))", "legendFormat": "5xx 比例"}]})
    if "mysql" in types:
        panels.append({"id": (pid := pid + 1), "title": "MySQL 主从延迟", "type": "timeseries",
                       "targets": [{"expr": "mysql_slave_status_seconds_behind_master", "legendFormat": "{{instance}}"}]})
    if "slo" in types:
        panels.append({"id": (pid := pid + 1), "title": "错误率 / SLO 预算", "type": "timeseries",
                       "targets": [{"expr": "job:http_errors:ratio_rate5m", "legendFormat": "错误率"},
                                    {"expr": str(args.error_budget), "legendFormat": "SLO 预算"}]})
    dash = {
        "title": "Ops Expert Dashboard",
        "uid": "ops-expert",
        "schemaVersion": 39,
        "version": 1,
        "refresh": "30s",
        "time": {"from": "now-6h", "to": "now"},
        "templating": {"list": [{"name": "datasource", "type": "datasource", "query": "prometheus"}]},
        "panels": panels,
    }
    return dash


def main():
    ap = argparse.ArgumentParser(description="生成 Prometheus 规则与 Grafana 面板脚手架")
    ap.add_argument("--type", default="node", help="逗号分隔: node,nginx,mysql,slo,all")
    ap.add_argument("--out", default="rules.yml", help="规则输出文件")
    ap.add_argument("--dashboard", default="", help="Grafana dashboard JSON 输出(可选)")
    ap.add_argument("--job", default="node", help="Prometheus job 标签值(用于 up 匹配)")
    ap.add_argument("--slo-metric", default="http_requests_total", help="SLO 计数指标")
    ap.add_argument("--slo-code", default="code", help="状态码 label 名")
    ap.add_argument("--error-budget", type=float, default=0.001, help="SLO 错误预算(如 0.001=99.9%)")
    ap.add_argument("--w-fast", default="5m", help="SLO 快窗口")
    ap.add_argument("--w-slow", default="1h", help="SLO 慢窗口")
    args = ap.parse_args()

    types = {t.strip() for t in args.type.split(",") if t.strip()}
    if "all" in types:
        types = {"node", "nginx", "mysql", "slo"}

    groups = build_groups(types, args)
    write_rules(args.out, groups)

    if args.dashboard:
        dash = build_dashboard(types, args)
        with open(args.dashboard, "w", encoding="utf-8") as f:
            json.dump(dash, f, ensure_ascii=False, indent=2)
        print(f"已生成面板: {args.dashboard} (panels={len(dash['panels'])})")


if __name__ == "__main__":
    main()
