@echo off
pushd "%~dp0"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Requirements install failed.
  pause
  exit /b 1
)
echo Requirements OK.
pause
