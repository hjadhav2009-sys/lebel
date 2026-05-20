@echo off
pushd "%~dp0"
python -m pip install --upgrade pyinstaller pyinstaller-hooks-contrib
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onedir --windowed --name MMS_Label_Tools --add-data "assets;assets" --add-data "marketplace_v12\reference_templates;marketplace_v12\reference_templates" --add-data "marketplace_v12\reference_templates\amazon\amazon_template.prn;reference_templates\amazon" --collect-all reportlab --collect-all fitz --collect-all pymupdf main.py
pause
