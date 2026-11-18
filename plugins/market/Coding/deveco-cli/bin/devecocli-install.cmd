@echo off
rem Copyright (c) 2026 Huawei Device Co., Ltd.
rem SPDX-License-Identifier: MIT
rem deveco-cli-plugin-entry
setlocal
set "DEVECO_PLUGIN_SCRIPT_DIR=%~dp0"
"%SystemRoot%\System32\where.exe" node.exe >nul 2>nul
if errorlevel 1 (
  >&2 echo Node.js was not found. Install Node.js 22 or later and retry.
  exit /b 2
)
node.exe "%~dp0..\runtime\main.mjs" install %*
exit /b %ERRORLEVEL%
