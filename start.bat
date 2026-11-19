@echo off
cd /d C:\laragon\www\api-scheduler

rem Tunggu PostgreSQL siap (cek port 5432 tiap 5 detik)
:wait
powershell -NoProfile -Command "if ((Test-NetConnection 127.0.0.1 -Port 5432 -WarningAction SilentlyContinue).TcpTestSucceeded) {exit 0} else {exit 1}"
if errorlevel 1 (
  ping -n 6 127.0.0.1 >nul
  goto wait
)

call venv\Scripts\activate
python -u -m uvicorn app.main:app --host 192.168.12.73 --port 8010 >> app.log 2>&1