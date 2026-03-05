@echo off
rem Run AutoITR with one command on Windows. Creates venv if needed and does first-time setup.

setlocal EnableDelayedExpansion
pushd "%~dp0"

rem Ensure Python is available
where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python not found in PATH. Install Python or add it to PATH.
  pause
  exit /b 1
)

rem Create virtualenv if it does not exist
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
)

rem Resolve venv python
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

rem First-time dependency setup (runs only once)
if not exist ".venv_setup_done" (
  echo Performing first-time venv setup. This may take several minutes...
  "%VENV_PY%" -m pip install --upgrade pip setuptools wheel
  rem Fix common numpy/opencv mismatch
  "%VENV_PY%" -m pip uninstall -y numpy opencv-python opencv-python-headless 2>nul
  "%VENV_PY%" -m pip install "numpy<2" opencv-python
  if exist requirements.txt (
    "%VENV_PY%" -m pip install -r requirements.txt
  )
  "%VENV_PY%" -m pip install PyMuPDF
  echo done > .venv_setup_done
)

echo Starting AutoITR (app_enhanced.py)...
"%VENV_PY%" app_enhanced.py

popd
endlocal