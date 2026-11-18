# 诊断完成后的清理清单

诊断 → 定位根因 → 修复后，**必须**逐项删除所有临时插桩，否则会污染发布版本（残留写文件、性能损耗、信息泄露）。

## 逐项删除

- [ ] 删除 `lib.rs` 中的 `dbg_log` 函数定义（版本 A 或 B）
- [ ] 删除所有 `dbg_log(...)` 调用（观测点 1/2/3 等）
- [ ] 删除 `debug_log` 命令函数
- [ ] 从 `invoke_handler(tauri::generate_handler![...])` 中移除 `debug_log` 注册
- [ ] 删除桥接层所有 `I.invoke('debug_log', ...)` 调用
- [ ] 删除桥接层 `listen` 中的埋点代码块
- [ ] 若为诊断临时加了 `chrono` 依赖，且项目其他地方未用，从 `Cargo.toml` 移除

## grep 自检（应无任何输出）

```bash
grep -rn "dbg_log\|debug_log" src-tauri/src/
grep -rn "debug_log" public/ 2>/dev/null
grep -rn "debug_log" src/ 2>/dev/null
```

## 构建产物自检

- [ ] 删除部署目录残留的 `debug.log`
- [ ] 重新编译：`touch src-tauri/src/lib.rs && cargo build --release`
- [ ] 重新部署 exe（**先 Stop-Process 关闭运行中的进程**，避免文件占用）
- [ ] 启动应用，正常操作，确认部署目录**不再生成** `debug.log`
- [ ] 确认目标功能正常（菜单响应、事件回调触发等）

## 常见遗漏

| 遗漏点 | 后果 |
|--------|------|
| `dbg_log` 函数删了但调用还在 | 编译失败 |
| 调用删了但 `debug_log` 命令还注册着 | 编译 warning，前端仍可写文件（安全隐患） |
| 桥接埋点只删了一半 | 前端每次 listen 都多一次 invoke，性能损耗 |
| 忘了重新 `touch lib.rs` | 部署的 exe 里前端仍是带埋点的旧版 |
| 忘了删部署目录的 `debug.log` | 误把上次诊断日志当成本次证据 |
