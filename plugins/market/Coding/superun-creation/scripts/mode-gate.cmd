:; exec sh "$(dirname "$0")/$(basename "$0" .cmd).sh" "$@" #
@echo off
setlocal EnableExtensions DisableDelayedExpansion
REM 仅发现宿主运行时，不安装工具。@author xiuyu.yi
set "_SUPERUN_NODE=%SUPERUN_KIT_NODE%"
if defined _SUPERUN_NODE goto run
for %%I in (node.exe) do set "_SUPERUN_NODE=%%~$PATH:I"
if defined _SUPERUN_NODE goto run
if not defined QODER_NODE_RUNTIME goto missing
set "_SUPERUN_NODE=%QODER_NODE_RUNTIME%"
set "ELECTRON_RUN_AS_NODE=1"
:run
if not exist "%_SUPERUN_NODE%" goto missing
"%_SUPERUN_NODE%" "%~dpn0.mjs" %*
exit /b %errorlevel%
:missing
if not "%~n0"=="prepare-cli" goto gate_missing
if "%~1"=="--hook" goto hook_missing
echo {"schemaVersion":1,"ok":false,"code":"NODE_REQUIRED","results":[]}
exit /b 1
:hook_missing
echo {"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"NODE_REQUIRED\uFF1A\u8BF7\u5BBF\u4E3B\u51C6\u5907 Node/npm\u540E\u91CD\u8BD5\u3002"}}
exit /b 0
:gate_missing
echo NODE_REQUIRED 1>&2
exit /b 2
