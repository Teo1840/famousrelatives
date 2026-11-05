@echo off
setlocal

title FamousRelatives Stopper

set "ROOT=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%stop-system.ps1" -Scope All

echo.
pause
