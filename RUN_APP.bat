@echo off
pushd "%~dp0"
python main.py
if errorlevel 1 pause
