@echo off
setlocal
set "PLUGIN_INSTALL_ROOT=%LARK_CLI_INSTALL_ROOT%"
if not defined PLUGIN_INSTALL_ROOT set "PLUGIN_INSTALL_ROOT=%USERPROFILE%\.local\share\qoder\lark-cli"

if defined LARK_CLI_RUNTIME_EXECUTABLE (
  if not exist "%LARK_CLI_RUNTIME_EXECUTABLE%" (
    >&2 echo LARK_CLI_RUNTIME_EXECUTABLE does not point to a usable runtime.
    exit /b 127
  )
  "%LARK_CLI_RUNTIME_EXECUTABLE%" %*
  exit /b
)

if exist "%PLUGIN_INSTALL_ROOT%\node_modules\@larksuite\cli\bin\lark-cli.exe" (
  "%PLUGIN_INSTALL_ROOT%\node_modules\@larksuite\cli\bin\lark-cli.exe" %*
  exit /b
)

for %%F in (
  "%USERPROFILE%\.qoder\bin\lark-cli.exe"
  "%USERPROFILE%\.qoder-cn\bin\lark-cli.exe"
) do if exist "%%~F" (
  "%%~F" %*
  exit /b
)

for /f "delims=" %%F in ('where lark-cli.exe 2^>nul') do (
  "%%F" %*
  exit /b
)

for /f "delims=" %%R in ('npm root -g 2^>nul') do if exist "%%R\@larksuite\cli\bin\lark-cli.exe" (
  "%%R\@larksuite\cli\bin\lark-cli.exe" %*
  exit /b
)

>&2 echo {"ok":false,"error":{"type":"runtime","subtype":"missing","message":"lark-cli is not installed","hint":"Ask the user for permission, then run lark-cli-install."}}
exit /b 127
