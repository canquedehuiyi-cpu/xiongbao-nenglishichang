---
name: hardware-embedded
displayName: "硬件与嵌入式交付"
description: >-
  软硬件交付团队的硬件与嵌入式工程技能：覆盖硬件架构与选型、电路/PCB 设计评审、固件与驱动(RTOS/裸机)、设备通信协议(MQTT/Modbus/串口/蓝牙)、软硬联调、板级资源与功耗约束、与后端接入(设备上报/控制)。
  命中硬件架构、选型、联调、软硬接口、协议、PCB、电路、固件、驱动、RTOS、实时性、设备上报等意图时调用。
  触发词：硬件、电路、PCB、器件、BOM、选型、联调、软硬接口、协议、固件、驱动、RTOS、嵌入式、实时性、设备上报、设备控制、Modbus、MQTT、串口、蓝牙、功耗、可制造性。
descriptionZh: >-
  硬件与嵌入式交付：硬件架构/选型/电路PCB、固件驱动RTOS、设备协议、软硬联调与后端接入。
descriptionEn: >-
  Hardware and embedded delivery: hardware architecture/selection/PCB, firmware/driver/RTOS, device protocols, soft-hard integration and backend ingestion.
tags:
  - 硬件
  - 嵌入式
  - 联调
  - 设备协议
---

# 硬件与嵌入式交付 (Hardware & Embedded Delivery)

本技能为团队硬件侧提供**可落地的工程方法**，与 `agents/` 中的路通远(硬件组长)/易图安(硬件)/褚固行(嵌入式)角色卡联动：角色卡定边界与协同，本技能给实现方法。

## 适用边界
- 硬件架构与器件选型、电路/PCB 设计评审、BOM 与可制造性。
- 固件/驱动、RTOS/裸机、实时性与资源受限约束。
- 设备通信协议（MQTT / Modbus / 串口 / 蓝牙 / CAN）与后端接入（设备上报 / 控制）。

## 工作流
1. **对齐软硬接口**：先与后端组长石磐安约定设备↔云端协议（字段、QoS、时序、失败重试），再动手固件。
2. **硬件方案**：路通远定架构与选型 → 易图安出电路/PCB/BOM；关注信号完整性、功耗、测试点、可制造性。
3. **固件实现**：褚固行落地驱动与任务调度，强调确定性与栈/内存预算。
4. **联调**：先板级自测（外设读写、看门狗、低功耗），再做软硬联调（协议联调、云端回环）。
5. **接入后端**：设备上报走石磐安定的接口契约；本协议与 `api-contract` 技能对齐。

## 产出约定
- 软硬接口文档：协议帧格式、字段表、时序图（mermaid ≤8.8.3）、异常与重传。
- PCB 评审清单：关键信号、电源树、测试点、ESD/EMC 注意点。
- 固件变更须可回滚（bootloader/双分区），联调问题记录可复现步骤。

## 与内置技能协同
- 设备云端接入的接口契约 → `api-contract`。
- 设备侧服务的部署与监控 → `team-ops-expert`。
- 涉及生产烧录/批量上线 → `devops-pipeline` 的发布剧本。
