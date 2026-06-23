@echo off
title Dictum — Setup
cd /d "%~dp0"

echo.
echo ============================================
echo  Dictum — Configurando entorno virtual
echo ============================================
echo.

:: Crear .venv si no existe
if not exist ".venv" (
    echo [1/4] Creando entorno virtual .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: No se pudo crear el entorno virtual.
        echo Asegurate de tener Python 3.10+ instalado.
        pause
        exit /b 1
    )
) else (
    echo [1/4] .venv ya existe, saltando creacion...
)

:: Activar .venv
echo [2/4] Activando .venv ...
call .venv\Scripts\activate.bat

:: Instalar requirements
echo [3/4] Instalando dependencias (requirements.txt) ...
pip install --upgrade pip
pip install -r requirements.txt

:: Instalar PyTorch con CUDA 11.8 (para faster-whisper)
echo [4/4] Instalando PyTorch con CUDA 11.8 ...
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

echo.
echo ============================================
echo  Setup completado con exito!
echo  Para correr el proyecto:
echo    .venv\Scripts\activate
echo    python main.py
echo ============================================
echo.
pause
