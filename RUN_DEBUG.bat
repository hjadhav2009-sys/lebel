@echo off
cd /d "%~dp0"
echo Starting debug mode...
echo If app closes or hangs, send screenshot of this window and logs\debug_log.txt
python app.py
pause
