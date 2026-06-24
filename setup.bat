@echo off
title Dictum — Setup
cd /d "%~dp0"

echo.
echo ============================================
echo  Dictum — Configuring virtual environment
echo ============================================
echo.

:: Create .venv if it doesn't exist
if not exist ".venv" (
    echo [1/4] Creating virtual environment .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Could not create virtual environment.
        echo Make sure you have Python 3.10+ installed.
        pause
        exit /b 1
    )
) else (
    echo [1/4] .venv already exists, skipping creation...
)

:: Activate .venv
echo [2/4] Activating .venv ...
call .venv\Scripts\activate.bat

:: Install requirements
echo [3/4] Installing dependencies (requirements.txt) ...
pip install --upgrade pip
pip install -r requirements.txt

:: Ask if PyTorch should be installed
echo.
echo [4/4] Optional PyTorch installation
echo Dictum uses ctranslate2 for GPU acceleration. If you already have CUDA Toolkit installed on your system, you don't need PyTorch.
echo However, if you want pip to download the CUDA DLLs automatically (weighs ~2.5GB),
echo installing PyTorch is the fastest way.
set /p INSTALL_PT="Do you want to install PyTorch to get the CUDA DLLs? (y/N): "
if /I "%INSTALL_PT%"=="y" (
    echo Installing PyTorch with CUDA 11.8 ...
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
) else (
    echo Skipping PyTorch installation.
)

echo.
echo ============================================
echo  Setup completed successfully!
echo  To run the project:
echo    .venv\Scripts\activate
echo    python main.py
echo ============================================
echo.
pause
