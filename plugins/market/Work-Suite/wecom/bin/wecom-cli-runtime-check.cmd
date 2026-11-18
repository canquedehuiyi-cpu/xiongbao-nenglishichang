@echo off
rem wecom-qoder-entrypoint
node "%~dp0..\runtime.cjs" check %*
exit /b %ERRORLEVEL%
