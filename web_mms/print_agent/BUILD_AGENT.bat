@echo off
setlocal
call .venv\Scripts\activate.bat
python -m PyInstaller --noconfirm --clean --onefile --name MMSPrintAgent agent_main.py
