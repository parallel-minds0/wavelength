@echo off
setlocal
if not exist "%~dp0runtime\python.exe" (
  powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\bootstrap-windows.ps1"
  if errorlevel 1 exit /b 1
)
"%~dp0runtime\python.exe" -I -B "%~dp0installer\entry.py" %*
exit /b %errorlevel%
