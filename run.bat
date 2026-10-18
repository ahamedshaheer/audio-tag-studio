@echo off
title Audio Tag Studio ^& Keyword Cleaner
cd /d "%~dp0"
echo ========================================================
echo        Starting Audio Tag Studio ^& Cleaner...
echo ========================================================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not found in PATH.
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

python server.py
if %errorlevel% neq 0 (
    echo.
    echo [NOTICE] If dependencies are missing, run:
    echo pip install -r requirements.txt
    echo.
    pause
)
