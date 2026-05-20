M Men Style Tool 2 - BarTender Style PRN / Direct Printing Guide

WHAT IS NEW IN V15
1. Tool 2 can generate native TSPL PRN files based on the real working BarTender PRN.
2. Tool 2 now has printer buttons:
   - Select Printer
   - Generate PRN Print File
   - Generate PRN & Print
   - Print Last PRN
3. PDF remains for preview/export. For barcode scanning, use PRN printing.

WHY PRN IS IMPORTANT
PDF printing passes through Windows scaling and printer driver conversion. Barcodes can become too thin, too thick, or merged.
PRN sends printer commands directly, like BarTender, so barcode quality is much closer to the original printer output.

WHAT YOUR REAL PRN SHOWED
Printer language: TSPL/TSC
Label size: 101.5 mm x 50 mm
Gap: 3 mm
Speed: 3
Density: 10
Barcode type: Code 39
Barcode command style: BARCODE x,y,"39",37,0,180,1,3,"VALUE"

HOW TO USE TOOL 2
1. Build EXE locally, not from network path.
2. Open MMS_Label_Tools.exe.
3. Open Tool 2 Marketplace Product Label Generator.
4. Upload Excel/CSV files.
5. Check preview if needed.
6. Click Select Printer and choose the same thermal printer used in BarTender.
7. Click Generate PRN & Print for direct printing.
8. Or click Generate PRN Print File to save the PRN first.

IMPORTANT WINDOWS SETUP
- Install the thermal printer driver in Windows.
- The printer must appear in Windows Printers & Scanners.
- Run INSTALL_REQUIREMENTS.bat once so pywin32 is installed.
- If direct print fails, generate PRN and ask printer uncle to test it manually.

OUTPUT FOLDER
Desktop\MMS_Label_Tools_Output\Marketplace_Product_PRN

WHEN TO USE PDF
Use PDF only for visual checking. Do not judge barcode scanning from PDF output.

WHEN TO USE PRN
Use PRN for real thermal printing and scanning.
