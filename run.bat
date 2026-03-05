@echo off
pushd "%~dp0"

rem Create virtual environment if it does not exist
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)

rem Run the app using the venv Python (no installs/uninstalls)
".venv\Scripts\python.exe" app_enhanced.py

popd