@echo off
title BA Copilot - local app
cd /d "%~dp0"
echo.
echo  ==============================================
echo    BA Copilot - starting the local app
echo  ==============================================
echo.

rem ---- find a working Python (py launcher first, then python)
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
  echo  Python 3.10 or newer is not installed.
  echo  Opening the download page. Install it, tick "Add python.exe to PATH",
  echo  then double-click this file again.
  start "" https://www.python.org/downloads/
  pause
  exit /b 1
)
echo  Using: %PY%

rem ---- private environment for this app (first run takes 1-2 minutes)
if not exist ".venv\Scripts\python.exe" (
  echo  Creating the app environment...
  %PY% -m venv .venv || (echo  Could not create the environment. & pause & exit /b 1)
)
echo  Installing / checking packages...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt || (echo  Package install failed - check your internet connection. & pause & exit /b 1)

rem ---- free port 8501 if an old copy is still running
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8501 " ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1

echo.
echo  Starting... your browser will open http://localhost:8501
echo  Keep this window open while you use the app. Close it to stop the app.
echo.
rem ---- open the browser once the server is up (headless mode skips Streamlit's email prompt)
start "" /min cmd /c "timeout /t 7 /nobreak >nul & start "" http://localhost:8501"
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false
pause
