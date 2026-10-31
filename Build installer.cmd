@echo off
setlocal
cd /d "%~dp0"
title Build aivillage installer
echo This creates a Windows installer from an existing Windows app build.
echo First run Build aivillage.cmd, then install Inno Setup 6.7 or newer from:
echo https://jrsoftware.org/isinfo.php
echo Existing installers will not be overwritten.
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" build_installer.py
) else (
  py -3.12 build_installer.py
)
if errorlevel 1 (
  echo.
  echo Installer build failed. Check the message above.
  pause
  exit /b 1
)
echo.
echo Installer complete. Look in dist\installers.
pause
