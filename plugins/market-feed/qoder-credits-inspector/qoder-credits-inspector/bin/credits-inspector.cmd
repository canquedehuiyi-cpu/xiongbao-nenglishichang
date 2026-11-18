@echo off
setlocal
rem credits-inspector.cmd - Windows launcher: locate a JS runtime and run the plugin scripts.
rem Two modes: "<launcher> cli <flags>" runs scripts\cli.mjs (user/Agent facing);
rem any other call runs scripts\hook.mjs (on-session-start / on-stop, used by hooks.json).
rem Runtime order: Qoder CN bundled Electron (ELECTRON_RUN_AS_NODE=1), then system node.exe.
rem Never requires node on PATH. If no runtime is found, exit 0 (a Stop hook must not block).
rem NOTE: keep this file ASCII-only. cmd.exe parses batch in the OEM code page, so non-ASCII
rem bytes can corrupt line parsing on some locales.

for %%I in ("%~dp0..") do set "plugin_root=%%~fI"

set "javascript_runtime="
set "electron_run_as_node="

if exist "%LOCALAPPDATA%\Programs\Qoder CN\Qoder CN.exe" set "javascript_runtime=%LOCALAPPDATA%\Programs\Qoder CN\Qoder CN.exe"
if defined javascript_runtime goto qoder_runtime
if exist "%ProgramFiles%\Qoder CN\Qoder CN.exe" set "javascript_runtime=%ProgramFiles%\Qoder CN\Qoder CN.exe"
if defined javascript_runtime goto qoder_runtime
if exist "C:\Program Files\Qoder CN\Qoder CN.exe" set "javascript_runtime=C:\Program Files\Qoder CN\Qoder CN.exe"
if defined javascript_runtime goto qoder_runtime

where node.exe >nul 2>nul
if errorlevel 1 goto no_runtime
set "javascript_runtime=node.exe"
set "electron_run_as_node=0"
goto runtime_selected

:qoder_runtime
set "electron_run_as_node=1"

:runtime_selected
if "%electron_run_as_node%"=="1" (set "ELECTRON_RUN_AS_NODE=1") else (set "ELECTRON_RUN_AS_NODE=")
set "entry=%plugin_root%\scripts\hook.mjs"
if /i "%~1"=="cli" set "entry=%plugin_root%\scripts\cli.mjs"
if /i "%~1"=="cli" shift
"%javascript_runtime%" "%entry%" %*
exit /b %errorlevel%

:no_runtime
exit /b 0
