@echo off
cd /d "%~dp0"
echo Installing build requirements...
python -m pip install -r requirements.txt
echo.
echo Building MarketplaceLabelGeneratorDebug ONEDIR console build...
python -m PyInstaller --noconfirm --onedir --console --name MarketplaceLabelGeneratorDebug ^
  --add-data "data\amazon_brand_rules.json;data" ^
  --add-data "data\amazon_category_rules.json;data" ^
  --add-data "data\branches.json;data" ^
  --add-data "data\label_formats.json;data" ^
  --hidden-import pandas ^
  --hidden-import openpyxl ^
  --hidden-import reportlab ^
  --hidden-import PIL ^
  --hidden-import win32print ^
  --hidden-import win32api ^
  app.py
echo.
echo Debug build complete:
echo dist\MarketplaceLabelGeneratorDebug\MarketplaceLabelGeneratorDebug.exe
pause
