@echo off
REM Arranca la app de certificados con doble clic.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app.py
) else (
  uv run --with flask --with openpyxl python app.py
)
pause
