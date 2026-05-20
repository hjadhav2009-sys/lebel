@echo off
cd /d "%~dp0"
echo Starting Marketplace Label Generator debug mode...
echo If app closes or hangs, send screenshot of this window and logs\debug_log.txt
python app.py
echo.
echo App closed. If there was an error, check logs\debug_log.txt.
pause
