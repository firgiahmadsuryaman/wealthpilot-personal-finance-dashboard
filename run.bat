@echo off
cd /d "%~dp0"
if not exist .venv (
  echo [1/3] Membuat virtual environment Python...
  py -3.10 -m venv .venv 2>nul
  if errorlevel 1 py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
 echo.
echo WealthPilot berjalan di http://127.0.0.1:8000
echo Hentikan dengan menekan CTRL+C.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
