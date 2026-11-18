# Tauri 调试专家

面向 **Tauri v2 无框架桌面应用**（纯 HTML/JS + 自写桥接，无 React/Vue/Svelte）的事件链路调试专家套件。它覆盖从 Rust `emit` 到前端 payload 的完整链路，内置「分层插桩 → 逐层判定断点 → 修复 → 清理」的工作流，以及 9 条高频陷阱的根因与修法。

> **免责声明：** 本套件辅助开发调试流程，插桩代码仅用于诊断，定位根因后必须按清理清单全部移除，不应带入发布版本。诊断结论请结合项目实际验证后采纳。

## 适用角色

- **Tauri 桌面应用开发者** — 定位"事件发出去了但前端不响应"这类没有任何报错的静默故障
- **桌面端维护 / 排查人员** — 快速判断断点到底在 Rust 侧、注册层还是回调层

## 快速命令

| 命令 | 说明 |
|------|------|
| `/桌面事件链路诊断` | 粘贴桥接 `listen` 片段或描述症状（如"emit 了但前端回调不触发"），按分层插桩流程定位断点在哪一层 |

## 技能

| 技能 | 说明 |
|------|------|
| 桌面事件链路诊断 | 以文件日志（`debug.log`）为观测手段，在 Rust `dbg_log` → 前端可调用 `debug_log` 命令 → 桥接 `listen` 埋点三个层次插桩，用 5 个观测点逐层判定断点。内置：EventTarget 序列化格式（`{kind:'Any'}`）、payload 双层包裹、托盘 `on_menu_event` 全局双重触发、`MenuBuilder` 无事件方法、前端改动不触发重编译、进程锁定、`WebView2Loader.dll` 缺失、MinGW 工具链丢失等 9 条陷阱的根因、源码依据与修法，并附构建-部署循环与清理自检命令 |

## 目录结构

```
Tauri调试专家/
├── .qoder-plugin/
│   └── plugin.json
├── README.md
└── skills/
    └── 桌面事件链路诊断/
        ├── SKILL.md
        └── references/
            ├── dbg-log-template.rs      # Rust 侧插桩模板
            ├── bridge-listen-patch.js   # 桥接层 listen 埋点补丁
            └── cleanup-checklist.md     # 诊断后清理清单与 grep 自检
```

## 适用前提

- Tauri v2 项目
- 前端为纯 HTML/JS（无框架）
- 使用自写桥接脚本（非官方 `@tauri-apps/api` npm 包）
- 桥接中使用了 `window.__TAURI_INTERNALS__`

> 使用官方 `@tauri-apps/api` 的项目不适用本套件——官方 API 已正确处理 EventTarget 与 payload 解包，本套件指向的两类头号陷阱在官方 API 下不存在。
