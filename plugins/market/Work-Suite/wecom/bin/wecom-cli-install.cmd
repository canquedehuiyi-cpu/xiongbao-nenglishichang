@echo off
rem wecom-qoder-entrypoint
node "%~dp0..\runtime.cjs" install %*
exit /b %ERRORLEVEL%
