@echo off
pushd "%~dp0"
python -m pip install --upgrade pyinstaller pyinstaller-hooks-contrib
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onedir --windowed --name MMS_Label_Tools --collect-all reportlab --collect-all fitz --collect-all pymupdf main.py
pause
