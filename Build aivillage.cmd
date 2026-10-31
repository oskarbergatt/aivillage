@echo off
setlocal
cd /d "%~dp0"
title Build aivillage
echo This builds a Windows app for this computer's processor.
echo It downloads Python packages to a temporary build environment.
echo The app will be written to the dist folder; existing builds are not replaced.
echo.
choice /c YN /m "Continue"
if errorlevel 2 exit /b 0
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" build_app.py --install
) else (
  py -3.12 build_app.py --install
)
if errorlevel 1 (
  echo.
  echo Build failed. Install Python 3.12 if it is not installed, then try again.
  pause
  exit /b 1
)
echo.
echo Build complete. Open the dist folder to find your app.
pause
