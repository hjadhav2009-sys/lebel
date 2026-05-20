MMS 3 Tools V5 - Single Window + Central Output + Better Cropper

WHAT IS FIXED IN V5
1. All tools run inside the same main application window.
   - Tool 1 and Tool 2 do not open a separate new EXE/window anymore.
   - Every tool has a Back button to return to dashboard.

2. App logo/icon improved.
   - EXE build uses assets/logo.ico.
   - Main Tk window also uses logo.png/iconphoto so taskbar/title icon is more reliable.
   - Windows AppUserModelID is set in main.py for taskbar icon stability.

3. Central output folder on Desktop:
   Desktop\MMS_Label_Tools_Output

   Subfolders:
   Amazon_Packing_Labels
   Marketplace_Product_Labels
   Flipkart_Amazon_Cropped_Labels
   Database
   Logs
   Raw_Uploads
   Temp

4. Tool 1 database is not disturbed.
   - Amazon packing label tool keeps its own existing database flow.
   - Only output naming/folder is organized.

5. Multi upload support:
   - Tool 1: multiple PDFs
   - Tool 2: multiple CSV/XLS/XLSX files
   - Tool 3: multiple PDFs and full multi-page PDFs

6. Cropper V5:
   - One manual crop box can be applied to all pages.
   - If one PDF has 100 pages, it creates 100 label pages.
   - Multiple uploaded PDFs can be combined into one output PDF.
   - Output is 100mm x 150mm.
   - Keep scan-safe proportion option is enabled by default to avoid barcode/QR stretching.

HOW TO USE
1. Extract the ZIP fully.
2. Double click INSTALL_REQUIREMENTS.bat once.
3. Double click RUN_APP.bat to test.
4. Double click BUILD_EXE.bat to create the EXE.

After build, send this full folder to job worker:
dist\MMS_Label_Tools

Do not send only MMS_Label_Tools.exe alone.
