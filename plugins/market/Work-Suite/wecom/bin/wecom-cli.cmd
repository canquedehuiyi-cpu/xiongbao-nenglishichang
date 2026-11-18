@echo off
rem wecom-qoder-entrypoint
node "%~dp0..\runtime.cjs" run %*
exit /b %ERRORLEVEL%
