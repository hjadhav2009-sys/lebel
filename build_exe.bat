@echo off
cd /d "%~dp0"
echo Installing build requirements...
python -m pip install -r requirements.txt
echo.
echo Building MarketplaceLabelGenerator ONEDIR release...
python -m PyInstaller marketplace_label_generator.spec --noconfirm
echo.
echo Build complete:
echo dist\MarketplaceLabelGenerator\MarketplaceLabelGenerator.exe
pause
