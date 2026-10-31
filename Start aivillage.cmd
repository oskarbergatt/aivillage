@echo off
setlocal
cd /d "%~dp0"
title aivillage
echo Starting aivillage...
echo.

if exist ".venv\Scripts\python.exe" goto check_dependencies
if exist ".venv" goto broken_environment

echo Setting up the game for the first time. This may take a few minutes.
py -3.12 -m venv .venv >nul 2>&1
if exist ".venv\Scripts\python.exe" goto check_dependencies
if exist ".venv" goto broken_environment
py -3.11 -m venv .venv >nul 2>&1
if exist ".venv\Scripts\python.exe" goto check_dependencies

echo Python 3.12 or 3.11 is required to run the game.
echo Please install Python 3.12 from https://www.python.org/downloads/
echo Then double-click this file again.
pause
exit /b 1

:broken_environment
echo The existing .venv folder does not contain a working Python installation.
echo It has not been changed. Please repair it or ask for help.
pause
exit /b 1

:check_dependencies
".venv\Scripts\python.exe" -c "import pygame, numpy, requests, feedparser, dotenv, pyttsx3" >nul 2>&1
if not errorlevel 1 goto launch
echo Installing the required game components. An internet connection is needed.
".venv\Scripts\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 ".venv\Scripts\python.exe" -m ensurepip
if errorlevel 1 goto install_error
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto install_error

:launch
".venv\Scripts\python.exe" run.py
if errorlevel 1 goto launch_error
exit /b 0

:install_error
echo.
echo Setup could not install the game components. Check your connection and try again.
pause
exit /b 1

:launch_error
echo.
echo The game could not start. The error message above may help identify the problem.
pause
exit /b 1
