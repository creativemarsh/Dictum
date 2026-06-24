@echo off
echo [Dictum DEV] Starting with auto-restart...
echo Any changes in .py files will automatically restart the app.
echo Ctrl+C to exit.
echo.

.venv\Scripts\watchmedo auto-restart ^
    --patterns="*.py" ^
    --ignore-patterns="*__pycache__*" ^
    --recursive ^
    -- .venv\Scripts\python.exe main.py
