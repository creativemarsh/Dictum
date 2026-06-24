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

:: Preguntar si instalar PyTorch
echo.
echo [4/4] Instalacion opcional de PyTorch
echo Dictum usa ctranslate2 para la GPU. Si ya tienes CUDA Toolkit instalado en tu sistema, no necesitas PyTorch.
echo Sin embargo, si quieres que pip descargue los DLLs de CUDA automaticamente (pesa ~2.5GB),
echo instalar PyTorch es la forma mas rapida.
set /p INSTALL_PT="¿Deseas instalar PyTorch para obtener los DLLs de CUDA? (s/N): "
if /I "%INSTALL_PT%"=="s" (
    echo Instalando PyTorch con CUDA 11.8 ...
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
) else (
    echo Saltando la instalacion de PyTorch.
)

echo.
echo ============================================
echo  Setup completado con exito!
echo  Para correr el proyecto:
echo    .venv\Scripts\activate
echo    python main.py
echo ============================================
echo.
pause
