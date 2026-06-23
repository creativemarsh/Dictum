@echo off
echo [Dictum DEV] Iniciando con auto-restart...
echo Cualquier cambio en archivos .py reinicia la app automaticamente.
echo Ctrl+C para salir.
echo.

.venv\Scripts\watchmedo auto-restart ^
    --patterns="*.py" ^
    --ignore-patterns="*__pycache__*" ^
    --recursive ^
    -- .venv\Scripts\python.exe main.py
