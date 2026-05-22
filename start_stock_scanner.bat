@echo off
title Emirates Pride — Stock Sheet Scanner
color 0A
cd /d "%~dp0"

echo.
echo  ============================================
echo   EMIRATES PRIDE STOCK SHEET SCANNER
echo  ============================================
echo.

:: ── Try Windows Python Launcher first (most reliable on Windows) ──
where py >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo  Installing required package...
    py -m pip install -q google-genai
    echo  Starting server...
    py stock_ocr_api.py
    goto :done
)

:: ── Try python command ────────────────────────────────────────────
where python >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo  Installing required package...
    python -m pip install -q google-genai
    echo  Starting server...
    python stock_ocr_api.py
    goto :done
)

:: ── Try common install locations ──────────────────────────────────
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
) do (
    if exist %%P (
        echo  Found Python at %%P
        %%P -m pip install -q google-generativeai
        %%P stock_ocr_api.py
        goto :done
    )
)

:: ── Python not found ──────────────────────────────────────────────
echo.
echo  ============================================
echo   ERROR: Python not found on this computer.
echo  ============================================
echo.
echo  Please install Python:
echo  1. Open Microsoft Store
echo  2. Search "Python 3.12"
echo  3. Click Install (it's free)
echo  4. Close this window and double-click again
echo.
pause
goto :eof

:done
echo.
echo  Server stopped. Press any key to exit.
pause >nul
