@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Membuat virtual environment Python...
  py -3.10 -m venv .venv 2>nul
  if errorlevel 1 py -3 -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
  echo GAGAL: Python tidak ditemukan. Pasang Python 3.10 atau lebih baru.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo GAGAL: Virtual environment tidak dapat diaktifkan.
  pause
  exit /b 1
)

if not exist ".env" copy ".env.example" ".env" >nul

echo [2/3] Memastikan dependensi terpasang...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo GAGAL: Instalasi dependensi gagal. Periksa koneksi internet dan versi Python.
  pause
  exit /b 1
)

echo.
echo WealthPilot berjalan di http://127.0.0.1:8000
echo Dokumentasi API: http://127.0.0.1:8000/docs
echo Hentikan dengan menekan CTRL+C.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
