M Men Style 3 Tool Label Software - V4 Output Structure Fixed

TOOLS
1. Amazon Packing Slip Label Generator
2. Marketplace Product Label Generator V12
3. Flipkart / Amazon Shipping Label Cropper

CENTRAL OUTPUT FOLDER
All normal generated output files go to:
Desktop\MMS_Label_Tools_Output

Folder structure:
Desktop\MMS_Label_Tools_Output\Amazon_Packing_Labels
Desktop\MMS_Label_Tools_Output\Marketplace_Product_Labels
Desktop\MMS_Label_Tools_Output\Flipkart_Amazon_Cropped_Labels
Desktop\MMS_Label_Tools_Output\Database
Desktop\MMS_Label_Tools_Output\Database\output_records
Desktop\MMS_Label_Tools_Output\Logs
Desktop\MMS_Label_Tools_Output\Raw_Uploads

IMPORTANT FOR TOOL 1
The Amazon Packing tool's own orders_database.csv is not disturbed.
Only generated PDF/latest-run CSV names are improved and recorded in central output history.

MULTIPLE UPLOAD SUPPORT
Amazon Packing Tool: multiple PDFs supported.
Marketplace V12 Tool: multiple CSV/XLS/XLSX files supported.
Flipkart/Amazon Cropper: multiple PDFs supported and full multi-page PDFs supported.

OUTPUT NAMING
Marketplace and Cropper tools ask for output name/purpose.
Output files include tool prefix + purpose + custom name + source/batch + date/time.
A central output history is saved here:
Desktop\MMS_Label_Tools_Output\Database\output_records\output_history.csv

HOW TO RUN
1. Extract ZIP
2. Double-click INSTALL_REQUIREMENTS.bat
3. Double-click RUN_APP.bat
4. To build EXE, double-click BUILD_EXE.bat

Final EXE folder after build:
dist\MMS_Label_Tools
Send the full folder to job worker, not only the EXE.

V6 note:
Auto crop has been tightened to crop only the shipping-label box. If a PDF format is unusual, use manual crop; manual selection still applies to every page and every selected PDF.


V18 DEBUG FINAL:
See README_V18_DEBUG_FINAL.txt and HOW_TO_USE_FINAL.txt.
Tool 2 barcode command was kept unchanged from the scanning version; only package cleanup and verification files were added.
