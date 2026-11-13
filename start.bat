@echo off
REM ---------------------------------------------------------------------------
REM  EquityPilot AI - one-click start for Windows
REM  First run: creates the Python environment, installs packages and builds the
REM  web app (a few minutes). Later runs start in seconds.
REM  Usage: double-click start.bat   (or run "start.bat" in a terminal)
REM ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"
set PORT=8000

REM --- already running? just open the browser
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo EquityPilot is already running on port %PORT%.
    start "" http://localhost:%PORT%/
    goto :eof
)

REM --- Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.11 or newer is required. Install it from https://www.python.org/downloads/
    echo         and tick "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating the Python environment ^(first run only^)...
    python -m venv .venv || goto :fail
)

".venv\Scripts\python.exe" -c "import fastapi, uvicorn, pandas, yfinance, sqlalchemy" >nul 2>&1
if errorlevel 1 (
    echo Installing Python packages ^(first run only, a few minutes^)...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
)

REM --- web app (only needs Node.js when it has not been built yet)
if not exist "web\dist\index.html" (
    where npm >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] The web app is not built yet and Node.js was not found.
        echo         Install Node.js 20+ from https://nodejs.org/ and run start.bat again.
        pause
        exit /b 1
    )
    echo Building the web app ^(first run only^)...
    pushd web
    call npm install || (popd & goto :fail)
    call npm run build || (popd & goto :fail)
    popd
)

echo.
echo Starting EquityPilot AI on http://localhost:%PORT%/  ^(press Ctrl+C to stop^)
echo The first start loads market data in the background; pages fill in within a minute.
start "" cmd /c "timeout /t 4 >nul & start "" http://localhost:%PORT%/"
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" -m uvicorn api.main:app --host 127.0.0.1 --port %PORT% --log-level warning
goto :eof

:fail
echo.
echo [ERROR] Setup failed - see the messages above. Check your internet connection and try again.
pause
exit /b 1
