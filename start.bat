@echo off
SETLOCAL EnableDelayedExpansion
TITLE "SwarmSec Integrated Launcher & Auto-Scaler"

:: ===============================
:: Config
:: ===============================
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "VENV_ACTIVATE=%PROJECT_DIR%\.venv\Scripts\activate.bat"
set "AE_DIR=%PROJECT_DIR%\models\experiments\ae"

cd /d "%PROJECT_DIR%"

echo ==========================================
echo   🚀 Launching SwarmSec Core Services
echo ==========================================

:: Start Core Services in Windows Terminal (as in startup.bat)
start "" wt ^
new-tab --title "Core Server :8000" cmd /k "cd /d %PROJECT_DIR% && call \"%VENV_ACTIVATE%\" && uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload" ^
; new-tab --title "Dashboard API :8001" cmd /k "cd /d %PROJECT_DIR% && call \"%VENV_ACTIVATE%\" && uvicorn dashboard.app.main:app --host 0.0.0.0 --port 8001 --reload" ^
; new-tab --title "Streamlit UI :8501" cmd /k "cd /d %PROJECT_DIR% && call \"%VENV_ACTIVATE%\" && streamlit run streamlit_global/app.py"

echo.
echo ==========================================
echo   🤖 Agent Auto-Scaler Started
echo   Monitoring: %AE_DIR%
echo ==========================================

:: To keep track of how many agents we've already launched
set "LAUNCHED_COUNT=0"

:CHECK_LOOP
:: 1. Count folders named run_* or runs_* in the AE directory
set "FOLDER_COUNT=0"
if exist "%AE_DIR%" (
    for /d %%D in ("%AE_DIR%\run_*") do (
        set /a FOLDER_COUNT+=1
    )
)

:: 2. Total required agents = 1 (default) + number of runs folders
set /a TOTAL_REQUIRED=FOLDER_COUNT + 1

:: 3. Check if we need to launch more agents
if !TOTAL_REQUIRED! GTR !LAUNCHED_COUNT! (
    echo [!] Detected !FOLDER_COUNT! experiment folders. Total agents required: !TOTAL_REQUIRED!
    
    :: Launch agents from LAUNCHED_COUNT+1 up to TOTAL_REQUIRED
    set /a START_IDX=LAUNCHED_COUNT + 1
    for /L %%I in (!START_IDX!, 1, !TOTAL_REQUIRED!) do (
        :: Format AGENT_ID (agent-001, agent-002, etc.)
        set "VAL=%%I"
        if %%I LSS 10 (
            set "AGENT_ID=agent-00%%I"
        ) else if %%I LSS 100 (
            set "AGENT_ID=agent-0%%I"
        ) else (
            set "AGENT_ID=agent-%%I"
        )

        echo [+] Launching !AGENT_ID! ...
        
        start wt -w 0 new-tab --title "!AGENT_ID!" cmd /k ^
        call "%VENV_ACTIVATE%" ^&^& ^
        cd /d "%PROJECT_DIR%" ^&^& ^
        python -u -m agent.run_agent --agent-id !AGENT_ID!

        set "LAUNCHED_COUNT=%%I"
    )
)

:: Wait for 5 seconds before next check
timeout /t 5 >nul
goto CHECK_LOOP
