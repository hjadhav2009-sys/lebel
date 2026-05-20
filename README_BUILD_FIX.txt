If EXE is not created, use BUILD_EXE.bat from this fixed ZIP.

Main fix:
The old BAT used: pyinstaller
On many Windows computers pyinstaller is installed but not added to PATH, so Windows says:
'pyinstaller' is not recognized.

This fixed BAT uses:
python -m PyInstaller

That runs PyInstaller through Python directly and works even when pyinstaller.exe is not in PATH.

Final EXE path:
dist\MMS_Label_Tools\MMS_Label_Tools.exe

Send the full folder to job worker:
dist\MMS_Label_Tools
Do not send only the EXE alone.
