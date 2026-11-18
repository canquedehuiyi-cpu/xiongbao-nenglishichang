---
name: 桌面事件链路诊断
version: 2.1.0
description: Diagnose event-chain failures in Tauri v2 framework-less (vanilla HTML + hand-written JS bridge) desktop apps — frontend never receives emitted events, menu/tray clicks do nothing, emit fires but the callback never runs, event listeners silently fail. Instruments each layer (Rust emit → on_menu_event → plugin:event|listen registration → transformCallback → frontend payload) with file logging to pinpoint which layer is broken. Triggers on: Tauri event, emit, listen, bridge, transformCallback, EventTarget, debug.log, vanilla Tauri.
description_zh: 诊断 Tauri v2 无框架（vanilla HTML + 自写 JS 桥接）应用的事件链路故障。当用户报告"前端收不到事件""菜单/托盘点击无反应""emit 了但回调没触发""事件监听不生效"等 Tauri 事件断裂问题时使用。按 Rust emit → on_menu_event → plugin:event|listen 注册 → transformCallback 回调 → 前端 payload 逐层插桩定位断点。关键词：Tauri 事件、emit、listen、桥接、transformCallback、EventTarget、debug.log、插桩、事件链路。
user-invocable: true
argument-hint: 粘贴桥接脚本的 listen 片段，或描述症状（如"emit 了但前端回调不触发"）
---

# Tauri v2 Vanilla 桥接事件链路调试

## 快速定位（先看这里）

绝大多数"Rust 侧 emit 了、前端回调却没触发"的根因是 **EventTarget 格式错误**（见 Pitfalls #1）：`plugin:event|listen` 的 `target` 传 `null` 时反序列化失败，**所有**事件监听器从未注册，且没有任何可见报错（Promise rejection 被吞掉）。

所以不要一上来就全面插桩，先花两分钟排除这一条：

```javascript
// 在桥接 listen 里加一行，看注册到底成没成功
await I.invoke('plugin:event|listen', { event, handler, target: { kind: 'Any' } })
  .then(() => console.log('listen OK', event))
  .catch((e) => console.log('listen FAIL', event, e));
```

出现 `listen FAIL` → 直奔 Pitfalls #1 修正 `target` 格式即可。只有注册正常、问题依然存在时，再按下面的分层插桩流程定位断点在**哪一层**。

> 注意："不依赖 payload 的监听器看着正常、依赖 payload 的全坏"是**错觉**——监听器其实全都没注册，只是部分功能不依赖事件也能工作。

## 适用场景

- Tauri v2 项目，前端为纯 HTML/JS（无 React/Vue/Svelte 框架）
- 使用自写桥接脚本（如 tauri-api.js）而非官方 @tauri-apps/api npm 包
- 症状：Rust 侧 emit 了事件但前端回调从未触发；菜单/托盘点击无反应；部分事件"正常"但依赖 payload 的全坏
- 无控制台 GUI 应用（windows_subsystem = "windows"），无法通过 stdout 观察运行时行为

## 前置确认

开始调试前，先确认项目属于 vanilla 桥接模式：

1. 检查前端目录是否有自写的桥接文件（通常叫 `tauri-api.js`、`bridge.js`、`tauri-bridge.js` 等）
2. 确认 `package.json` 中**没有** `@tauri-apps/api` 依赖（有则走官方 API，不适用本技能）
3. 确认桥接中使用了 `window.__TAURI_INTERNALS__`（`transformCallback`、`invoke` 等）
4. 确认 `tauri.conf.json` 的 `build.frontendDist` 指向本地静态目录（编译时嵌入）
5. 记录关键路径：项目根目录、Rust 源码（通常 `src-tauri/src/lib.rs`）、前端资源目录、构建产物路径

## Steps：分层插桩工作流

### 第 1 步：插入 Rust 侧文件日志函数

在 `lib.rs` 中插入临时 `dbg_log` 函数（放在常量区之后、业务代码之前）：

```rust
/* ═══════════════ 临时调试日志（诊断完删除）═══════════════ */

fn dbg_log(msg: &str) {
    use std::io::Write;
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let path = dir.join("debug.log");
            if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(path) {
                let ts = chrono::Local::now().format("%H:%M:%S%.3f");
                let _ = writeln!(f, "[{}] {}", ts, msg);
            }
        }
    }
}
```

注意：需要 `chrono = "0.4"` 依赖。若项目未引入 chrono，可改用 `std::time::SystemTime` 简化版：

```rust
fn dbg_log(msg: &str) {
    use std::io::Write;
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let path = dir.join("debug.log");
            if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(path) {
                let _ = writeln!(f, "{:?}", msg);
            }
        }
    }
}
```

### 第 2 步：在事件链路各节点插桩

根据要诊断的链路，在关键节点插入 `dbg_log` 调用。典型的菜单→前端动作链路有 5 个观测点：

```rust
// 观测点 1：命令入口（前端 invoke 触发）
#[tauri::command]
fn show_context_menu(app: AppHandle, window: tauri::Window) {
    dbg_log("[1] show_context_menu 被调用");
    match build_context_menu(&app) {
        Ok(menu) => {
            dbg_log("[1] 菜单构建成功，准备 popup");
            let _ = menu.popup(window);
            dbg_log("[1] popup 返回");
        }
        Err(e) => dbg_log(&format!("[1] 菜单构建失败: {e}")),
    }
}

// 观测点 2：app 级事件分发
.on_menu_event(|app, event| {
    dbg_log(&format!("[2] on_menu_event 收到: {}", event.id().as_ref()));
    handle_menu_action(app, event.id().as_ref());
})

// 观测点 3：动作处理 + emit
fn handle_menu_action(app: &AppHandle, id: &str) {
    dbg_log(&format!("[3] handle_menu_action: {}", id));
    match id {
        "greet" | "walk" | "dance" => {
            dbg_log(&format!("[3] emit action {}", id));
            let _ = app.emit("action", id);
            dbg_log("[3] emit 完成");
        }
        // ...
    }
}
```

### 第 3 步：注册前端可调用的日志命令

在 `lib.rs` 中添加并注册 `debug_log` 命令，让前端 JS 也能写入同一个 debug.log：

```rust
/* 临时调试：前端日志写文件（诊断完删除） */
#[tauri::command]
fn debug_log(msg: String) {
    dbg_log(&format!("[前端] {}", msg));
}
```

注册到 `invoke_handler`：

```rust
.invoke_handler(tauri::generate_handler![
    // ... 已有命令 ...
    debug_log,  // 临时
])
```

### 第 4 步：桥接层埋点

在自写桥接的 `listen` 方法中，`transformCallback` 回调里记录 Tauri 传入的原始事件对象：

```javascript
async listen(event, callback) {
    const id = ++listenerId;
    const handler = I.transformCallback(e => {
        // 临时调试（诊断完删除）：记录原始事件对象
        I.invoke('debug_log', {
            msg: JSON.stringify({ event, rawType: typeof e, raw: e })
        }).catch(() => {});
        callback({ event, id, payload: e.payload });
    });
    // 注意 target 格式！见 Pitfalls
    await I.invoke('plugin:event|listen', { event, handler, target: { kind: 'Any' } });
    return id;
}
```

同时在 `listen` 注册前后加日志，确认注册是否成功：

```javascript
async listen(event, callback) {
    const id = ++listenerId;
    I.invoke('debug_log', { msg: `[bridge] listen 注册: ${event}, id=${id}` }).catch(() => {});
    const handler = I.transformCallback(e => { /* ... */ });
    try {
        await I.invoke('plugin:event|listen', { event, handler, target: { kind: 'Any' } });
        I.invoke('debug_log', { msg: `[bridge] listen 注册成功: ${event}` }).catch(() => {});
    } catch (err) {
        I.invoke('debug_log', { msg: `[bridge] listen 注册失败: ${event} → ${err}` }).catch(() => {});
    }
    return id;
}
```

### 第 5 步：强制重编译 + 部署

前端资源通过 `generate_context!` 在编译时嵌入 exe。仅改 .js/.html 不会触发 cargo 重编译。

```bash
# 关键：touch lib.rs 强制 generate_context! 重新嵌入前端资源
touch src-tauri/src/lib.rs

# 编译（根据项目调整路径和工具链）
cd <PROJECT_ROOT>/src-tauri && cargo build --release 2>&1 | tail -15

# 部署（根据项目调整产物路径）
cp -f target/release/<CRATE_NAME>.exe <DEPLOY_PATH>/<APP_NAME>.exe
```

部署前清除旧日志：`rm -f <DEPLOY_PATH>/debug.log`

### 第 6 步：用户操作 + 读取日志

请用户执行触发操作（如右键→点菜单项），然后读取 debug.log：

```bash
cat <DEPLOY_PATH>/debug.log
```

### 第 7 步：逐层断点判定

根据日志输出判断断点位置：

| 日志表现 | 断点位置 | 根因方向 |
|---------|---------|---------|
| debug.log 不存在 | 前端回调从未触发 | 事件监听器根本没注册成功 → 查 EventTarget 格式（见 Pitfalls #1） |
| 有 [bridge] listen 注册失败 | plugin:event\|listen 调用报错 | 查错误信息，通常是 target 格式或权限问题 |
| 有 Rust [1][2][3] 日志但无 [前端] 日志 | emit 成功但前端监听器未注册 | 同上，或 listen 注册时 target 格式错误导致静默失败 |
| 有 [前端] 日志但 raw 是对象 `{event,payload,id}` | 桥接层 payload 解包错误 | 见 Pitfalls #2（payload 双层包裹） |
| 日志中每个事件出现两次 | 事件被重复处理 | 见 Pitfalls #3（on_menu_event 全局双重触发） |
| 有 [1] 但无 [2] | 菜单事件未分发到 app 级监听器 | 检查 Builder::on_menu_event 是否注册；MenuBuilder 无此方法（Pitfalls #4） |
| 有 [2] 但无 [3] | handle_menu_action 未被调用或 id 不匹配 | 检查菜单项 id 与 match 分支是否一致 |

### 第 8 步：修复 + 清理

定位根因并修复后，必须清理所有临时代码：

1. 删除 `dbg_log` 函数定义
2. 删除所有 `dbg_log(...)` 调用
3. 删除 `debug_log` 命令及其在 invoke_handler 中的注册
4. 删除桥接中的 `I.invoke('debug_log', ...)` 调用
5. 重新编译部署，验证功能正常且无残留日志输出

验证清理完成：
```bash
grep -r "dbg_log\|debug_log" src-tauri/src/   # 应无输出
grep "debug_log" public/                        # 应无输出
```

## 构建-部署循环参考

每次改代码后的标准迭代流程（根据具体项目调整路径）：

```bash
# 1. 关闭运行中的进程（Windows 用 PowerShell，避免中文进程名 GBK 乱码）
powershell -NoProfile -Command "Get-Process | Where-Object { $_.Path -like '*<PROCESS_KEYWORD>*' } | Stop-Process -Force" 2>/dev/null

# 2. 编译（Bash tool timeout 设 600000ms）
export PATH="<TOOLCHAIN_PATH>:$HOME/.cargo/bin:$PATH" && cd "<PROJECT_ROOT>/src-tauri" && cargo build --release 2>&1 | tail -15

# 3. 部署
cd "<PROJECT_ROOT>" && cp -f "src-tauri/target/release/<CRATE_NAME>.exe" "<APP_NAME>.exe" && rm -f debug.log

# 4. 启动并验证
start "" "<APP_NAME>.exe" && sleep 3 && powershell -NoProfile -Command "Get-Process | Where-Object { $_.Path -like '*<PROCESS_KEYWORD>*' } | Select-Object Id"
```

## Pitfalls

### 1. EventTarget 格式错误（最隐蔽，优先级最高）

Tauri v2 的 `EventTarget` 是 `#[serde(tag = "kind")]` 标签枚举。vanilla 桥接中传 `target: null` 无法反序列化，`plugin:event|listen` 命令直接报错，**所有事件监听器从未注册成功**——但不会有任何可见错误（Promise rejection 被吞掉）。

正确写法：`target: { kind: 'Any' }`

EventTarget 各变体的序列化形式：
- `EventTarget::Any` → `{"kind": "Any"}`
- `EventTarget::WebviewWindow { label }` → `{"kind": "WebviewWindow", "label": "main"}`
- `EventTarget::Webview { label }` → `{"kind": "Webview", "label": "main"}`

诊断线索：如果"不依赖 payload 的监听器看似正常，依赖 payload 的全坏"——这其实是错觉，所有监听器都没注册，只是某些功能不依赖事件也能工作。

### 2. payload 双层包裹

Tauri 的 `runCallback(handlerId, eventData)` 传给 `transformCallback` 回调的是**完整事件对象** `{event, payload, id}`，不是裸 payload。

错误写法：`transformCallback(e => callback({ event, id, payload: e }))`  → 前端 `e.payload` 拿到的是对象
正确写法：`transformCallback(e => callback({ event, id, payload: e.payload }))` → 前端 `e.payload` 拿到真实负载

源码依据：`tauri-<version>/scripts/core.js` 中 `runCallback(id, data)` 直接调用 `callback(data)`，而 `data` 是 `event_initialization_script` 中构造的 `{event: eventName, payload: serializedPayload, id: listenerId}`。

### 3. 托盘 on_menu_event 全局双重触发

`TrayIconBuilder::on_menu_event` 的文档明确写着 "this handler is called for any menu event"——它和 `Builder::on_menu_event` 一样注册进 `global_event_listeners`，是**全局**的，不是托盘专属。

如果同时挂了 app 级和托盘级两个 `on_menu_event`，每个菜单点击（无论来自右键菜单还是托盘菜单）都会被处理两次。

解决：只保留 `Builder::on_menu_event`（app 级）一个，在其中统一处理所有菜单 id。

### 4. MenuBuilder 无 on_menu_event

Tauri v2 的 `MenuBuilder`（用于构建弹出式右键菜单）**没有** `on_menu_event` 方法。弹出式菜单的事件必须走 app 级 `Builder::on_menu_event` 统一分发。

### 5. 前端改动不触发重编译

Tauri 的前端资源通过 `generate_context!` 宏在**编译时**嵌入 exe。只改 .html/.js 而不改 .rs 文件时，cargo 认为无需重编译，exe 中嵌入的仍是旧版前端。

解决：`touch src/lib.rs`（或任何被 `generate_context!` 引用的 .rs 文件）强制触发重编译。

### 6. 启动弹终端窗口

`main.rs` 必须有 `#![windows_subsystem = "windows"]`，否则 GUI 程序启动时附带黑色控制台窗口。

### 7. 进程锁定导致部署失败

不关进程就 cp 覆盖 exe → "Text file busy" 或权限错误。永远先 Stop-Process。Windows 下用 PowerShell 的 `Get-Process | Stop-Process`，不要用 taskkill（中文进程名 GBK 乱码）。

### 8. WebView2Loader.dll 缺失

exe 启动即退、无窗口无报错。部署时必须确认 `WebView2Loader.dll` 与 exe 同目录。

### 9. MinGW 环境丢失（GNU 工具链）

若使用 `x86_64-pc-windows-gnu` 目标，`/tmp/mingw64` 在系统重启后可能被清理。`cargo build` 报 linker 错误时检查 `ls /tmp/mingw64/mingw64/bin/gcc.exe`，缺失则需重新解压 MinGW。

## Verification

1. 构建成功：`cargo build --release` 输出无 error，tail 显示 `Compiling <crate>` + `Finished`
2. 部署完整：exe 和 WebView2Loader.dll 同目录，exe 大小合理（通常 >10MB）
3. 启动成功：Get-Process 返回进程 ID，应用窗口可见
4. 调试有效：操作后 debug.log 存在且包含预期节点的日志行
5. 修复验证：目标功能正常工作（如菜单点击有响应、事件回调触发）
6. 清理完成：`grep -r "dbg_log\|debug_log" src-tauri/src/` 无输出，`grep "debug_log" public/` 无输出
7. 最终构建：清理后重新编译部署，确认无残留调试代码影响性能或安全

## 参考模板

以下模板可直接复制使用，作为上面各步骤的起点：

- [Rust 侧插桩模板](references/dbg-log-template.rs) — 两版 `dbg_log`（chrono / 无依赖 std）、`debug_log` 命令、命令入口与 `on_menu_event` / `handle_menu_action` 观测点骨架
- [桥接层 listen 埋点补丁](references/bridge-listen-patch.js) — 记录原始事件对象 + 注册成败；附 EventTarget 各变体序列化速查
- [清理清单](references/cleanup-checklist.md) — 诊断完成后的逐项清理与 grep 自检命令
