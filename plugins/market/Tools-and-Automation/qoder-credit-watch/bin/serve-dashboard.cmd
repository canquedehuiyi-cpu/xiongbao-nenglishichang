@echo off
setlocal
rem serve-dashboard.cmd - Windows launcher for the local dashboard server.
rem Starts scripts\serve-dashboard.mjs, which serves dashboard\site and exposes the
rem loopback-only refresh API used by the site's buttons.
rem Locates a JS runtime on its own: Qoder CN's bundled Electron first
rem (ELECTRON_RUN_AS_NODE=1), then node.exe from PATH. Never requires node on PATH.
rem Arguments pass through: --site <dir> --port <n>
rem NOTE: keep this file ASCII-only and CRLF-terminated. cmd.exe parses batch in the
rem OEM code page (cp936 on zh-CN), so non-ASCII bytes can corrupt line parsing.

for %%I in ("%~dp0..") do set "plugin_root=%%~fI"

set "javascript_runtime="

if exist "%LOCALAPPDATA%\Programs\Qoder CN\Qoder CN.exe" set "javascript_runtime=%LOCALAPPDATA%\Programs\Qoder CN\Qoder CN.exe"
if defined javascript_runtime goto qoder_runtime
if exist "%ProgramFiles%\Qoder CN\Qoder CN.exe" set "javascript_runtime=%ProgramFiles%\Qoder CN\Qoder CN.exe"
if defined javascript_runtime goto qoder_runtime
if exist "C:\Program Files\Qoder CN\Qoder CN.exe" set "javascript_runtime=C:\Program Files\Qoder CN\Qoder CN.exe"
if defined javascript_runtime goto qoder_runtime

where node.exe >nul 2>nul
if errorlevel 1 goto no_runtime
set "javascript_runtime=node.exe"
goto runtime_selected

:qoder_runtime
set "ELECTRON_RUN_AS_NODE=1"

:runtime_selected
"%javascript_runtime%" "%plugin_root%\scripts\serve-dashboard.mjs" %*
exit /b %errorlevel%

:no_runtime
echo Neither Qoder CN's bundled runtime nor node.exe was found.
echo Run this with node directly: node "%plugin_root%\scripts\serve-dashboard.mjs"
exit /b 1
