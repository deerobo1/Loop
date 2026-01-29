LANMeet - Windows Executable Files
=====================================

This folder contains COMPLETELY STANDALONE Windows executable files for LANMeet.

FILES:
------
1. LANMeet_Setup.exe    - OPTIONAL environment setup (for development only)
2. LANMeet_Server.exe   - STANDALONE conference server application
3. LANMeet_Client.exe   - STANDALONE client application with GUI

🚀 QUICK START (NO SETUP REQUIRED):
----------------------------------
1. START THE SERVER:
   - Double-click "LANMeet_Server.exe"
   - The server will start on port 5001 by default
   - Keep this window open while using the application
   - Press Ctrl+C to stop the server

2. START CLIENT(S):
   - Double-click "LANMeet_Client.exe"
   - You can run multiple clients for different users
   - Use the GUI to create or join meetings

⚠️  SETUP IS NO LONGER REQUIRED:
-------------------------------
- LANMeet_Setup.exe is now OPTIONAL (only needed for Python development)
- Server and Client executables are COMPLETELY STANDALONE
- No virtual environment needed
- No Python installation required
- All dependencies are bundled inside the executables

REQUIREMENTS:
------------
- Windows 10 or later
- NO Python installation required
- NO virtual environment needed
- NO additional dependencies needed

TROUBLESHOOTING:
---------------
- If executables don't run, try running as administrator
- Check Windows Defender/antivirus isn't blocking the executables
- Executables are large (~100MB each) because they contain all dependencies
- First run may be slower as Windows extracts the bundled files

NOTES:
------
- ✅ ALL EXECUTABLES ARE COMPLETELY STANDALONE
- ✅ NO SETUP REQUIRED - just run server and client directly
- ✅ Server must be running before clients can connect
- ✅ Executables work independently of Python source files
- ✅ No virtual environment or Python installation needed
- ✅ All dependencies (PyQt6, OpenCV, NumPy, etc.) are bundled inside

MAJOR IMPROVEMENTS:
------------------
- ✅ Server and Client are now COMPLETELY STANDALONE
- ✅ No virtual environment dependency
- ✅ No Python installation required
- ✅ All dependencies bundled inside executables
- ✅ Setup is now optional (only for development)
- ✅ Instant run - no installation process needed
- ✅ Login dialog is now RESIZABLE with dynamic content adjustment
- ✅ Improved UI scaling for different screen sizes and resolutions

For support or issues, check the original Python files and documentation.