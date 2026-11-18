: << 'CMDBLOCK'
@echo off
REM Cross-platform hook launcher.
REM Windows: cmd.exe runs the batch part below.
REM macOS/Linux: /bin/sh skips this block and calls run-sync.sh.
REM Usage: run-sync.cmd [check]
setlocal
set "SCRIPT=%~dp0..\scripts\qodercli_sync.py"
set "CHECK="
if /i "%~1"=="check" set "CHECK=1"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>nul
  if not errorlevel 1 (
    if defined CHECK exit /b 0
    py -3 "%SCRIPT%" --hook --quiet >nul 2>nul
    exit /b 0
  )
)

where python >nul 2>nul
if %errorlevel%==0 (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>nul
  if not errorlevel 1 (
    if defined CHECK exit /b 0
    python "%SCRIPT%" --hook --quiet >nul 2>nul
    exit /b 0
  )
)

if defined CHECK (
  echo [qodercli-session-sync] Python 3.8+ not found, automatic sync is disabled. 1>&2
  echo   Windows: install from https://www.python.org/downloads/ and tick "Add python.exe to PATH". 1>&2
  echo   Manual sync: python scripts\qodercli_sync.py --cwd "<project>" 1>&2
  echo   See the plugin README section "Dependencies". 1>&2
)
exit /b 0
CMDBLOCK

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 0
exec sh "${SCRIPT_DIR}/run-sync.sh" "$@"
