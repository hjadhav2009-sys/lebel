@echo off
setlocal
call .venv\Scripts\activate.bat
python -m mms_print_agent.app %*
