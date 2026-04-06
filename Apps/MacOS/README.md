Basic Info:
macos_install.sh -> Installer script
snaprename.py -> The main python application script which launches the main.py
Snap Rename.app -> The Application itself (Compiled from snaprename.py)
Snap Rename.workflow -> Finder Quick Action workflow to open selected folder in app.
srename.sh -> Shell script to open the app in terminal.

NOTE: To Compile Into an app:
1. Copy snaprename.py to Python Version folder
2. Install pyinstaller: pip install pyinstaller
3. Run -> python3 -m PyInstaller --windowed --name "Snap Rename" --icon=logo.icns --osx-bundle-identifier in.satvik-web.snaprename --add-data "main.py:." --add-data "tui.py:." --add-data "engine.py:." --add-data "utils.py:." --add-data "logo.png:." snaprename.py

Important Notes:

Snap Rename.workflow is to be placed in ~/Library/Services/

srename.sh is to be placed in /usr/local/bin/

symlink srename.sh -> srename to get srename under path. 

macos_install.sh installs the entire app

DO NOT Launch the Snap Rename.app here! Always launch it from Applications.

macos_app.zip -> contains the compiled app, the workflow and the shell script(srename.sh).

The installer actually downloads this zip and then installs everything!

How to install?
1. Download macos_installer.sh from GitHub Releases.
2. Open Terminal and navigate to the folder where you downloaded the file.
3. Run chmod +x macos_installer.sh
4. Run ./macos_installer.sh
5. Follow the instructions on the screen.