@echo off
setlocal
set "PLUGIN_INSTALL_ROOT=%LARK_CLI_INSTALL_ROOT%"
if not defined PLUGIN_INSTALL_ROOT set "PLUGIN_INSTALL_ROOT=%USERPROFILE%\.local\share\qoder\lark-cli"

if defined LARK_CLI_RUNTIME_EXECUTABLE (
  if not exist "%LARK_CLI_RUNTIME_EXECUTABLE%" (
    >&2 echo LARK_CLI_RUNTIME_EXECUTABLE does not point to a usable runtime.
    exit /b 1
  )
  echo %LARK_CLI_RUNTIME_EXECUTABLE%
  exit /b 0
)

if exist "%PLUGIN_INSTALL_ROOT%\node_modules\@larksuite\cli\bin\lark-cli.exe" (
  echo %PLUGIN_INSTALL_ROOT%\node_modules\@larksuite\cli\bin\lark-cli.exe
  exit /b 0
)

for %%F in (
  "%USERPROFILE%\.qoder\bin\lark-cli.exe"
  "%USERPROFILE%\.qoder-cn\bin\lark-cli.exe"
) do if exist "%%~F" (
  echo %%~F
  exit /b 0
)

for /f "delims=" %%F in ('where lark-cli.exe 2^>nul') do (
  echo %%F
  exit /b 0
)

for /f "delims=" %%R in ('npm root -g 2^>nul') do if exist "%%R\@larksuite\cli\bin\lark-cli.exe" (
  echo %%R\@larksuite\cli\bin\lark-cli.exe
  exit /b 0
)

>&2 echo lark-cli runtime is not installed
exit /b 1
