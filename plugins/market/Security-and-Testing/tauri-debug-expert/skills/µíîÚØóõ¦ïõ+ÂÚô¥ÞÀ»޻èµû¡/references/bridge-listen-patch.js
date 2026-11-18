// ═══════════════ 桥接层 listen 埋点补丁模板（诊断完删除）═══════════════
//
// 在自写桥接（tauri-api.js / bridge.js 等）的 listen 方法中埋点。
// 记录三件事：注册请求、注册结果、Tauri 传入的原始事件对象。
//
// 关键点：
//   1. target 必须是 { kind: 'Any' }，传 null 会静默失败（见 Pitfalls #1）
//   2. transformCallback 回调收到的是完整事件对象 {event, payload, id}，
//      不是裸 payload（见 Pitfalls #2）

async listen(event, callback) {
    const id = ++listenerId;

    // [埋点 A] 注册请求
    I.invoke('debug_log', {
        msg: `[bridge] listen 注册: ${event}, id=${id}`
    }).catch(() => {});

    const handler = I.transformCallback(e => {
        // [埋点 C] Tauri 传入的原始事件对象
        try {
            I.invoke('debug_log', {
                msg: JSON.stringify({ event, rawType: typeof e, raw: e })
            }).catch(() => {});
        } catch (_) {}
        callback({ event, id, payload: e.payload });
    });

    // [埋点 B] 注册结果
    try {
        await I.invoke('plugin:event|listen', {
            event,
            handler,
            target: { kind: 'Any' }   // ← 必须是这个格式
        });
        I.invoke('debug_log', {
            msg: `[bridge] listen 注册成功: ${event}`
        }).catch(() => {});
    } catch (err) {
        I.invoke('debug_log', {
            msg: `[bridge] listen 注册失败: ${event} → ${err}`
        }).catch(() => {});
    }

    return id;
}

// ═══════════════ EventTarget 各变体的序列化形式（速查）═══════════════
//
//   EventTarget::Any                      → { kind: 'Any' }
//   EventTarget::WebviewWindow { label }  → { kind: 'WebviewWindow', label: 'main' }
//   EventTarget::Webview { label }        → { kind: 'Webview', label: 'main' }
//
// 错误示范（无法反序列化，plugin:event|listen 直接报错，Promise 被吞）：
//   target: null
//   target: 'Any'
//   target: { type: 'Any' }   // 字段名是 kind 不是 type
