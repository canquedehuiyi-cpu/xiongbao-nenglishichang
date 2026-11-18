:; exec "${0%/*}/ifs-suite-hook.sh" "$@" #
@echo off
setlocal EnableExtensions DisableDelayedExpansion
REM if Studio AI 智能创作 (if-Studio-AI-Creation) polyglot hook launcher (cmd/sh dual-syntax), single entry for both OSes.
REM Pattern after the official qodersec-launch.cmd polyglot.
REM
REM Unix (macOS/Linux): bash -c execs this file; the kernel sees no shebang (ENOEXEC),
REM   the shell falls back to /bin/sh, line 1 execs ifs-suite-hook.sh and never reaches
REM   the batch below. Line 1 uses ${0%/*} (pure builtin) instead of dirname so the
REM   delegation works even with a stripped PATH.
REM Windows: cmd.exe runs the batch below and delegates to Git Bash's bash when
REM   available (Qoder on Windows uses Git Bash as its shell; the same POSIX script
REM   then runs on Windows). When bash cannot be found, this launcher drains the
REM   piped stdin JSON and exits 0 - the hook degrades silently (non-blocking), and
REM   the agent self-reads config/platform.json + preferences.json per SKILL.md
REM   section 1 (fallback contract).
REM Keep this file CRLF-terminated: cmd.exe corrupts LF-only polyglot parsing.
REM Keep this file ASCII-only: cmd.exe batch text is decoded with the OEM codepage.
REM
set "SCRIPT_DIR=%~dp0"
set "SH_SCRIPT=%SCRIPT_DIR%ifs-suite-hook.sh"
set "BASH_EXE="
where bash >nul 2>nul && set "BASH_EXE=bash"
if not defined BASH_EXE if exist "%ProgramFiles%\Git\bin\bash.exe" set "BASH_EXE=%ProgramFiles%\Git\bin\bash.exe"
if not defined BASH_EXE if exist "%ProgramFiles(x86)%\Git\bin\bash.exe" set "BASH_EXE=%ProgramFiles(x86)%\Git\bin\bash.exe"
if not defined BASH_EXE if exist "%LocalAppData%\Programs\Git\bin\bash.exe" set "BASH_EXE=%LocalAppData%\Programs\Git\bin\bash.exe"
if not defined BASH_EXE goto :no_bash
"%BASH_EXE%" "%SH_SCRIPT%" %*
exit /b %ERRORLEVEL%
:no_bash
REM The hook host pipes the event JSON to stdin and expects it to be consumed.
REM Gate on QODER_PLUGIN_ROOT: present means a hook pipe, absent means somebody
REM is running this launcher by hand from a console (where `more` would block).
if defined QODER_PLUGIN_ROOT more >nul 2>nul
exit /b 0
