@echo off
TITLE SwarmSec Phase 2.1 Launcher

set PROJECT_DIR=D:\PROJECT_PHASE2\Phase2.1
set VENV_ACTIVATE=%PROJECT_DIR%\.venv\Scripts\activate.bat


cd /d %PROJECT_DIR%


start "SwarmSec Core Server :8000" cmd /k ^
call "%VENV_ACTIVATE%" ^&^& ^
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload


start "SwarmSec Dashboard API :8001" cmd /k ^
call "%VENV_ACTIVATE%" ^&^& ^
uvicorn dashboard.app.main:app --host 0.0.0.0 --port 8001 --reload


start "SwarmSec Streamlit UI" cmd /k ^
call "%VENV_ACTIVATE%" ^&^& ^
streamlit run streamlit_global/app.py

echo.
echo 🚀 SwarmSec Phase 2.1 services started
echo - Core Server      : http://localhost:8000
echo - Dashboard API    : http://localhost:8001
echo - Streamlit UI     : http://localhost:8501
echo.
pause
