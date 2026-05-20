MMS Label Tools V6 fixes

Fixed from V5:
1. Flipkart/Amazon auto crop now detects only the outer shipping-label border and stops before invoice/billing area.
2. Manual crop is kept exactly because it was working well.
3. Scan-safe proportion is ON by default so barcode/QR is not stretched badly.
4. Tool loading has a fail-safe error screen. If Tool 1 or Tool 2 fails, it will show the exact error instead of a black screen.
5. Runtime Windows AppID updated for better taskbar icon stability.
6. All tools still save output to Desktop/MMS_Label_Tools_Output.

Important:
- If you run RUN_APP.bat, Windows may show the Python/feather icon because it is running Python.
- After BUILD_EXE.bat, the built MMS_Label_Tools.exe should show the logo because PyInstaller uses assets/logo.ico.
- Send the full dist/MMS_Label_Tools folder to job workers, not only the exe.
