@echo off
setlocal

if defined LARK_CLI_RUNTIME_EXECUTABLE (
  >&2 echo LARK_CLI_RUNTIME_EXECUTABLE is set. Update that runtime or unset the override before installing.
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  >&2 echo npm is required to install lark-cli. Install Node.js/npm, then retry.
  exit /b 1
)

set "INSTALL_ROOT=%LARK_CLI_INSTALL_ROOT%"
if not defined INSTALL_ROOT set "INSTALL_ROOT=%USERPROFILE%\.local\share\qoder\lark-cli"
set "PACKAGE_SPEC=%LARK_CLI_PACKAGE_SPEC%"
if not defined PACKAGE_SPEC set "PACKAGE_SPEC=@larksuite/cli@1.0.98"
set "TARGET=%INSTALL_ROOT%\node_modules\@larksuite\cli\bin\lark-cli.exe"

call npm install --prefix "%INSTALL_ROOT%" --no-audit --no-fund --omit=dev "%PACKAGE_SPEC%"
if errorlevel 1 exit /b %ERRORLEVEL%

if not exist "%TARGET%" (
  >&2 echo lark-cli installation completed but the runtime was not found.
  exit /b 1
)

"%TARGET%" --version >nul
if errorlevel 1 exit /b %ERRORLEVEL%
echo %TARGET%
