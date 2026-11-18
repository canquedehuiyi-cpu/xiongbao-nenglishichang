@echo off
rem Copyright (c) 2026 Huawei Device Co., Ltd.
rem SPDX-License-Identifier: MIT
rem deveco-cli-plugin-entry
setlocal EnableExtensions EnableDelayedExpansion
set "DEVECO_PLUGIN_SCRIPT_DIR=%~dp0"
"%SystemRoot%\System32\where.exe" node.exe >nul 2>nul
if errorlevel 1 (
  set "launcher=%~dp0devecocli.cmd"
  echo {"schemaVersion":1,"status":"node-missing","host":{"platform":"win32","runtimeVariant":"cross-platform"},"launcher":"!launcher:\=/!","actions":[{"action":"install-node"}],"error":{"code":"node-missing","message":"Node.js was not found. Install Node.js 22 or later and retry."}}
  exit /b 2
)
node.exe "%~dp0..\runtime\main.mjs" check %*
exit /b %ERRORLEVEL%
