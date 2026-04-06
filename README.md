# Snap Rename

Snap Rename is a high-performance, cross-platform batch file renaming suite designed to handle everything from simple cleanup to complex, multi-stage metadata-driven renaming. It offers a unified experience across three distinct interfaces: a GUI, TUI, and a Web Application.

### About Snap Rename
- **Modular Pipeline Architecture**: Stack multiple rename tools into a single workflow. Chain "Clean Name" with "Add Prefix" and "Metadata Tagging" to see a live preview of the combined result before touching your disk.
- **Intelligent Metadata Handling**: Dynamically rename files using embedded information like Artist/Album (ID3), Camera Model/Date Taken (EXIF), or custom patterns parsed directly from filenames.
- **Zero-Dependency Engine**: The core engine and metadata extractors are written in pure Python and JavaScript, making the application lightweight, portable, and extremely fast on any hardware.
- **Seamless System Integration**: Features native integration with Windows File Explorer, MacOS Finder, and Linux systems for instant right-click access to the renaming suite from any folder.
- **Safety First Architecture**: Every batch operation is automatically logged to a persistent Undo history, allowing you to revert complex renames at any time without data loss.

## Installation and Setup

### Windows
- **Installer**: [Download windows_installer.exe](https://github.com/Satvik-web/Snap-Rename/releases/download/v1.0.0/windows_installer.exe)
- Run the installer to set up Snap Rename and follow on screen instructions.

### MacOS
- **Install Script**: [Download macos_install.sh](https://github.com/Satvik-web/Snap-Rename/releases/download/v1.0.0/macos_install.sh)
- Open Terminal in the download folder and run:
  1. `chmod +x macos_install.sh`
  2. `./macos_install.sh`

### Linux
- **Installer**: [Download linux_installer.sh](https://github.com/Satvik-web/Snap-Rename/releases/download/v1.0.0/linux_installer.sh)
- Open Terminal in the download folder and run:
  1. `chmod +x linux_installer.sh`
  2. `./linux_installer.sh`

### Python Edition (Source)
- **Source Zip**: [Download Python_Edition.zip](https://github.com/Satvik-web/Snap-Rename/releases/download/v1.0.0/Python_Edition.zip)
- Extract the zip, install dependencies (`pip install PyQt6 textual`), and run `python main.py --gui`.

## Application

### Terminal Commands (CLI/TUI)
Once installed, you can use the `srename` command directly in your terminal:
- `srename -d [Working Directory]`: Opens the TUI application in the specified folder.
- `srename --gui`: Opens the Desktop GUI.
- `srename --gui -d [Working Directory]`: Opens the GUI directly in the specified folder.
- If run without the `-d` flag, the app will prompt you to select or browse for a directory.

### Windows File Explorer Integration
- Select a folder in Explorer.
- Right-click and select **Show Other Options** (Windows 11) and then look for **Snap Rename** in the menu.
- This instantly opens the selected folder in the application.

### Mac Finder Integration
- Select a folder in Finder.
- Right-click and select **Quick Actions > Snap Rename**.
- This performs a context-aware launch into the chosen directory.

### OS Native Support
- On Windows, Linux, and MacOS, you can find Snap Rename in your **Start Menu** or **Applications** folder after installation. Launching it this way will prompt you to browse for a target workspace.

## Web Version
Snap Rename is fully functional in the browser:
- Navigate to the `Website/` directory and open `index.html`.
- [Open Web App](file:///Users/satvikrajnarayanan/Snap%20Rename/Website/index.html)
- It uses the modern File System Access API, allowing you to pick a local folder and rename files with zero installation. Recommended for Chromium-based browsers.

## Key Features
- **Pipeline Workflow**: Chain multiple tools (Clean -> Metadata -> Numbering) into a single execution.
- **Smart Metadata**: Extract artist, album, camera model, or resolution tags directly from the file bytes.
- **Live Preview**: See exact changes in a "before and after" table before hitting apply.
- **Undo System**: Every batch operation is logged, allowing you to revert changes at any time.

## TUI Notes

Snap Rename features a high-performance Terminal User Interface (TUI) built with the Textual framework, mirroring the full functionality of the GUI.

### Keyboard Shortcuts
Mastering these shortcuts allows for lightning-fast batch renaming without touching a mouse:

| Key | Action |
| :--- | :--- |
| `d` | **Directory**: Open a modal to change the working folder |
| `p` | **+Pipeline**: Add the current tool settings to the active pipeline |
| `a` | **Apply**: Run the entire pipeline on every file in the directory |
| `u` | **Undo**: Revert the last batch rename operation |
| `c` | **Clear**: Remove all steps from the current pipeline |
| `r` | **Remove Step**: Delete the last added operation from the pipeline |
| `1` - `6` | **Switch Tools**: Quickly jump between Clean, Smart, Normal, etc. |
| `q` | **Quit**: Exit the application safely |

### Key Features
- **Live Preview**: The "Live Preview" box updates instantly as you type regex patterns or toggle checkboxes, showing exactly how the first file in your list will be affected.
- **Visual Feedback**: The file table highlights pending changes in bold red and uses icons/status flags for conflicts and missing files.
- **Pipeline Workflow**: Build complex, multi-step renaming rules by stacking operations. The TUI recalculates the entire chain in real-time.
- **Cross-Platform Safety**: Optimized for maximum compatibility across Windows CMD/PowerShell, macOS Terminal, and Linux shells.

### Command Palette & Shortcuts

Snap Rename includes built-in "Spotlight" style searching to help you navigate features and documentation quickly.

#### TUI Command Palette (Ctrl+P)
In the Terminal UI, you can trigger the Command Palette by pressing Ctrl + P (or Cmd + P on macOS) or by clicking the small circle icon in the top-left corner.
- **Search Actions**: Type the name of any tool (e.g., "Smart", "Clean") or action (e.g., "Apply", "Undo") to jump to it instantly.
- **No Shortcuts Needed**: If you forget a keyboard binding, the palette lists all available commands in a searchable list.
