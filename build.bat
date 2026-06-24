@echo off
title Dictum — Build
cd /d "%~dp0"

echo.
echo ============================================
echo  Dictum — Generating executable
echo ============================================
echo.

call .venv\Scripts\activate.bat

echo Cleaning previous builds...
if exist "dist\Dictum" rmdir /s /q "dist\Dictum"
if exist "build\Dictum" rmdir /s /q "build\Dictum"

echo Compiling...
pyinstaller Dictum.spec --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: Build failed. Check the messages above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build successful!
echo  Executable at: dist\Dictum\Dictum.exe
echo ============================================
echo.
pause
