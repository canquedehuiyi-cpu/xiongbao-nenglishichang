/* ═══════════════ 临时调试日志（诊断完删除）═══════════════
 *
 * 用法：整块粘贴到 lib.rs 常量区之后、业务代码之前。
 * 有 chrono 依赖时用带时间戳版；否则用简化版。
 */

// ── 版本 A：带时间戳（需要 chrono = "0.4"）──
fn dbg_log(msg: &str) {
    use std::io::Write;
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let path = dir.join("debug.log");
            if let Ok(mut f) = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(path)
            {
                let ts = chrono::Local::now().format("%H:%M:%S%.3f");
                let _ = writeln!(f, "[{}] {}", ts, msg);
            }
        }
    }
}

// ── 版本 B：无额外依赖 ──
fn dbg_log(msg: &str) {
    use std::io::Write;
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let path = dir.join("debug.log");
            if let Ok(mut f) = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(path)
            {
                let _ = writeln!(f, "{}", msg);
            }
        }
    }
}

/* ═══════════════ 前端可调用的日志命令（诊断完删除）═══════════════
 *
 * 注册：把 debug_log 加进 .invoke_handler(tauri::generate_handler![...])
 */
#[tauri::command]
fn debug_log(msg: String) {
    dbg_log(&format!("[前端] {}", msg));
}

/* ═══════════════ 事件链路 5 个观测点（按需插入）═══════════════ */

// 观测点 1：命令入口
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

// 观测点 2：app 级事件分发（Builder::on_menu_event）
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
        other => dbg_log(&format!("[3] 未匹配的菜单 id: {other}")),
    }
}
