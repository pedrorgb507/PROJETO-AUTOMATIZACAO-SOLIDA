@echo off
title FINART - Automacao CTP
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run_ctp.py
) else (
    python run_ctp.py
)
echo.
echo O programa parou. Pressione uma tecla para fechar.
pause >nul
