@echo off
TITLE SwarmSec Phase 2.1 Launcher

:: ===============================
:: Force launcher to run as Admin
:: ===============================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit
)

:: ===============================
:: Config
:: ===============================
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "VENV_ACTIVATE=%PROJECT_DIR%\.venv\Scripts\activate.bat"

cd /d %PROJECT_DIR%

echo ==========================================
echo   🚀 Launching SwarmSec (Admin Mode)
echo ==========================================

:: ===========================================
:: Start Core Services in Windows Terminal
:: ===========================================

start "" wt ^
new-tab --title "Core Server :8000" cmd /k "cd /d %PROJECT_DIR% && call \"%VENV_ACTIVATE%\" && uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload" ^
; new-tab --title "Dashboard API :8001" cmd /k "cd /d %PROJECT_DIR% && call \"%VENV_ACTIVATE%\" && uvicorn dashboard.app.main:app --host 0.0.0.0 --port 8001 --reload" ^
; new-tab --title "Streamlit UI :8501" cmd /k "cd /d %PROJECT_DIR% && call \"%VENV_ACTIVATE%\" && streamlit run streamlit_global/app.py"

:: ===============================
:: Agent Launcher
:: ===============================

set AGENT_COUNT=1

:START_AGENT

if %AGENT_COUNT% LSS 10 (
    set AGENT_NAME=agent-00%AGENT_COUNT%
) else if %AGENT_COUNT% LSS 100 (
    set AGENT_NAME=agent-0%AGENT_COUNT%
) else (
    set AGENT_NAME=agent-%AGENT_COUNT%
)

echo Launching %AGENT_NAME% ...

start wt -w 0 new-tab --title "%AGENT_NAME%" cmd /k ^
call "%VENV_ACTIVATE%" ^&^& ^
cd /d %PROJECT_DIR% ^&^& ^
python -u -m agent.run_agent --agent-id %AGENT_NAME%

set /a AGENT_COUNT+=1

echo.
set /p ADD_MORE=Do you need another agent? (y/n): 

if /I "%ADD_MORE%"=="Y" goto START_AGENT

echo.
echo ==========================================
echo   ✅ SwarmSec Fully Running
echo ==========================================
echo   Core Server   → http://localhost:8000
echo   Dashboard API → http://localhost:8001
echo   Streamlit UI  → http://localhost:8501
echo ==========================================

pause