---
name: network-topology
displayName: "网络拓扑"
description: >-
  软硬件交付团队的网络拓扑技能：产出物理/逻辑网络拓扑——VPC/子网/网关/NAT/负载均衡/防火墙/链路与网段划分，标注带宽、延迟、冗余与故障域。
  区别于 team-ops-expert 的主机与监控：本技能聚焦网络结构与链路。命中国网络拓扑、VPC、子网、网关、负载均衡、网段、链路、故障域等意图时调用。
  触发词：网络拓扑、拓扑图、VPC、子网、网关、NAT、负载均衡、LB、防火墙、网段、链路、带宽、延迟、冗余、故障域、网络分区。
descriptionZh: >-
  网络拓扑：物理/逻辑拓扑，VPC/子网/网关/LB/链路，标注带宽延迟与故障域。
descriptionEn: >-
  Network topology: physical/logical topology, VPC/subnet/gateway/LB/links, bandwidth/latency and failure domains.
tags:
  - 网络拓扑
  - VPC
  - 负载均衡
  - 链路
---

# 网络拓扑 (Network Topology)

本技能为团队产出**网络结构与链路视图**，与 `agents/` 中的常守恒(运维)/石磐安(后端组长)角色卡及 `team-ops-expert` 技能联动：`team-ops-expert` 管主机与监控，本技能管网络形态。

## 适用边界
- 物理/逻辑网络拓扑：VPC、子网、网关、NAT、负载均衡、防火墙、DNS、链路与网段划分。
- 标注带宽、延迟、冗余路径、故障域与隔离边界。

## 工作流
1. **分层**：先分物理层（机房/机柜/上联）与逻辑层（VPC/子网/路由），不要混在一张图。
2. **边界对齐**：与常守恒确认公网/内网/隔离区，与石磐安确认服务暴露面与端口。
3. **产出拓扑**：用 mermaid（见 `design-diagrams`）或图形化表达；节点含角色、网段、关键设备。
4. **标注指标**：每条关键链路标带宽/延迟/冗余；标出单点故障与故障域。
5. **安全视图**：叠加防火墙/ACL/零信任边界，与 `team-ops-expert` 安全加固一致。

## 产出约定
- 逻辑拓扑图（VPC/子网/网关/LB/服务）与物理拓扑图（可选）。
- 网段规划表：CIDR、用途、路由、ACL 摘要。
- 风险清单：单点、故障域、跨区延迟、隔离缺口。

## 与内置技能协同
- 图示语法与校验 → `design-diagrams`。
- 主机/监控/安全闸门 → `team-ops-expert`。
- 发布链路演练 → `devops-pipeline`。
