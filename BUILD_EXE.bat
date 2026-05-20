@echo off
setlocal
pushd "%~dp0"

echo ==================================================
echo Building M Men Style 3 Tool Label Software EXE
echo ==================================================
echo.

echo Installing / checking requirements...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ERROR: Requirements install failed.
  pause
  exit /b 1
)

echo.
echo Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MMS_Label_Tools.spec del /q MMS_Label_Tools.spec

echo.
echo Building EXE using python -m PyInstaller...
python -m PyInstaller ^
  --noconfirm ^
  --onedir ^
  --windowed ^
  --name MMS_Label_Tools ^
  --icon "assets\logo.ico" ^
  --add-data "assets;assets" ^
  --add-data "marketplace_v12\data;marketplace_v12\data" ^
  --add-data "marketplace_v12\samples;marketplace_v12\samples" ^
  --add-data "marketplace_v12\reference_templates;marketplace_v12\reference_templates" ^
  --add-data "marketplace_v12\reference_templates\amazon\amazon_template.prn;reference_templates\amazon" ^
  --collect-all reportlab ^
  --collect-submodules reportlab.graphics.barcode ^
  --hidden-import reportlab.graphics.barcode.code128 ^
  --hidden-import reportlab.graphics.barcode.code39 ^
  --hidden-import reportlab.graphics.barcode.code93 ^
  --hidden-import reportlab.graphics.barcode.codabar ^
  --hidden-import reportlab.graphics.barcode.eanbc ^
  --hidden-import reportlab.graphics.barcode.qr ^
  --hidden-import PIL._tkinter_finder ^
  --hidden-import win32print ^
  --hidden-import win32api ^
  --hidden-import win32con ^
  main.py

if errorlevel 1 (
  echo.
  echo ==================================================
  echo BUILD FAILED. EXE was NOT created.
  echo Send this screen/log to ChatGPT.
  echo ==================================================
  pause
  exit /b 1
)

echo.
echo ==================================================
echo BUILD SUCCESSFUL.
echo EXE folder:
echo %cd%\dist\MMS_Label_Tools\MMS_Label_Tools.exe
echo.
echo Send the FULL folder below to job worker:
echo %cd%\dist\MMS_Label_Tools
echo ==================================================
pause
