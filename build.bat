@echo off
title Dictum — Build
cd /d "%~dp0"

echo.
echo ============================================
echo  Dictum — Generando ejecutable
echo ============================================
echo.

call .venv\Scripts\activate.bat

echo Limpiando builds anteriores...
if exist "dist\Dictum" rmdir /s /q "dist\Dictum"
if exist "build\Dictum" rmdir /s /q "build\Dictum"

echo Compilando...
pyinstaller Dictum.spec --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: Fallo el build. Revisa los mensajes de arriba.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build exitoso!
echo  Ejecutable en: dist\Dictum\Dictum.exe
echo ============================================
echo.
pause
