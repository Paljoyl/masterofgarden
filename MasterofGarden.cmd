@echo off
chcp 65001 >nul
setlocal
set "MOG_RELEASE_MODE=gui"
set "MOG_RELEASE_OFFLINE="
if /I "%~1"=="--check" set "MOG_RELEASE_MODE=check"
if /I "%~1"=="--check-ui" set "MOG_RELEASE_MODE=check-ui"
if /I "%~1"=="--setup-python" set "MOG_RELEASE_MODE=setup-python"
if /I "%~2"=="--offline" set "MOG_RELEASE_OFFLINE=-Offline"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher\bootstrap.ps1" -Mode "%MOG_RELEASE_MODE%" %MOG_RELEASE_OFFLINE%
set "MOG_RELEASE_EXIT=%errorlevel%"
if /I "%MOG_RELEASE_MODE%"=="gui" if not "%MOG_RELEASE_EXIT%"=="0" pause
exit /b %MOG_RELEASE_EXIT%
