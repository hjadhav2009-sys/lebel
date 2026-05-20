MMS 3 Tools V7 - Black Screen + Icon Fixed

Fixed in this version:
1. Tool 1 and Tool 2 black screen bug fixed.
   - The old code used self._root which conflicts with Tkinter internals.
   - Changed to self.root_window in Amazon and Marketplace tools.

2. Tool 1 and Tool 2 now open from the same dashboard window.
   - No second EXE is launched.
   - Use Back button to return to dashboard.

3. Logo/icon fixed.
   - assets/logo.ico is now a real Windows ICO file.
   - assets/logo.png is now a real PNG file.
   - BUILD_EXE.bat uses --icon assets\logo.ico.

4. Tool 3 auto crop is kept from V6 because it was working properly.

5. Central output folder remains:
   Desktop\MMS_Label_Tools_Output

How to use:
1. Extract this ZIP fully.
2. Double-click INSTALL_REQUIREMENTS.bat
3. Double-click RUN_APP.bat to test.
4. Double-click BUILD_EXE.bat to create EXE.

Final EXE folder:
dist\MMS_Label_Tools

Send the full dist\MMS_Label_Tools folder to job worker, not only the EXE file.
