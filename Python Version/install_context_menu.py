"""
Snap Rename — Context Menu & CLI Installer
Registers `snaprename` as a system command and adds right-click menu for folders.

After install:
  snaprename                     (TUI)
  snaprename --gui               (PyQt6 GUI)
  snaprename -d "/path"          (TUI + folder)
  snaprename --gui -d "/path"    (GUI + folder)

Supports: macOS · Windows · Linux
"""

import os, sys, re, stat, shutil, subprocess
from pathlib import Path

_HERE     = Path(__file__).resolve().parent
_MAIN_PY  = _HERE / "main.py"
_MARKER   = _HERE / ".context_menu_installed"
_LABEL    = "Snap Rename"
_CMD_NAME = "snaprename"


# ═══════════════════════════════════════════════════════════════
#  CLI command registration
# ═══════════════════════════════════════════════════════════════

def _get_python():
    return shutil.which("python3") or sys.executable

def _install_cli_unix():
    python = _get_python()
    wrapper = _HERE / _CMD_NAME
    wrapper.write_text(
        f'#!/usr/bin/env bash\n'
        f'# Snap Rename CLI wrapper\n'
        f'exec "{python}" "{_MAIN_PY}" "$@"\n',
        encoding="utf-8")
    wrapper.chmod(0o755)

    # Find writable bin dir
    candidates = [Path.home() / ".local" / "bin", Path("/usr/local/bin")]
    target_dir = None
    for d in candidates:
        if d.exists() and os.access(str(d), os.W_OK):
            target_dir = d
            break
    if target_dir is None:
        target_dir = Path.home() / ".local" / "bin"
        target_dir.mkdir(parents=True, exist_ok=True)

    link = target_dir / _CMD_NAME
    if link.exists() or link.is_symlink():
        link.unlink()
    try:
        link.symlink_to(wrapper)
    except OSError:
        shutil.copy2(str(wrapper), str(link))
        link.chmod(0o755)

    # Add to PATH in shell profile
    _ensure_path_unix(target_dir)
    return True, f"   CLI: `{_CMD_NAME}` → {link}"

def _ensure_path_unix(bin_dir):
    bin_str = str(bin_dir)
    if bin_str in os.environ.get("PATH", ""):
        return
    shell = os.environ.get("SHELL", "/bin/bash")
    if "zsh" in shell:
        rc = Path.home() / ".zshrc"
    elif "fish" in shell:
        rc = Path.home() / ".config" / "fish" / "config.fish"
    else:
        # Bash — macOS uses .bash_profile, Linux uses .bashrc
        if sys.platform == "darwin":
            rc = Path.home() / ".bash_profile"
        else:
            rc = Path.home() / ".bashrc"
    if not rc.exists():
        rc.touch()
    text = rc.read_text(encoding="utf-8")
    marker = "# Snap Rename PATH"
    if marker not in text:
        if "fish" in shell:
            line = f'\n{marker}\nset -gx PATH "{bin_str}" $PATH\n'
        else:
            line = f'\n{marker}\nexport PATH="{bin_str}:$PATH"\n'
        rc.write_text(text + line, encoding="utf-8")

def _install_cli_windows():
    wrapper = _HERE / f"{_CMD_NAME}.bat"
    wrapper.write_text(
        f'@echo off\nREM Snap Rename CLI wrapper\n'
        f'"{sys.executable}" "{_MAIN_PY}" %*\n',
        encoding="utf-8")
    try:
        import winreg, ctypes
        env_key = winreg.OpenKeyEx(
            winreg.HKEY_CURRENT_USER, r"Environment", 0,
            winreg.KEY_READ | winreg.KEY_SET_VALUE)
        current_path, _ = winreg.QueryValueEx(env_key, "Path")
        here_str = str(_HERE)
        if here_str.lower() not in current_path.lower():
            new_path = current_path.rstrip(";") + ";" + here_str
            winreg.SetValueEx(env_key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            # Broadcast change to System
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", 2, 1000, None)
        winreg.CloseKey(env_key)
    except Exception:
        pass
    return True, f"   CLI: `{_CMD_NAME}` → {wrapper}"

def _uninstall_cli_unix():
    w = _HERE / _CMD_NAME
    if w.exists(): w.unlink()
    for d in (Path.home() / ".local" / "bin", Path("/usr/local/bin")):
        link = d / _CMD_NAME
        if link.exists() or link.is_symlink(): link.unlink()

def _uninstall_cli_windows():
    w = _HERE / f"{_CMD_NAME}.bat"
    if w.exists(): w.unlink()

def install_cli():
    if sys.platform == "win32":
        return _install_cli_windows()
    return _install_cli_unix()

def uninstall_cli():
    if sys.platform == "win32":
        _uninstall_cli_windows()
    else:
        _uninstall_cli_unix()


# ═══════════════════════════════════════════════════════════════
#  macOS Finder Quick Action
# ═══════════════════════════════════════════════════════════════

def _macos_workflow_path():
    return Path.home() / "Library" / "Services" / "Snap Rename.workflow"

def _build_info_plist():
    return '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>NSServices</key>
    <array>
        <dict>
            <key>NSMenuItem</key>
            <dict>
                <key>default</key>
                <string>Snap Rename</string>
            </dict>
            <key>NSMessage</key>
            <string>runWorkflowAsService</string>
            <key>NSSendFileTypes</key>
            <array>
                <string>public.item</string>
                <string>public.folder</string>
                <string>com.apple.cocoa.path</string>
            </array>
        </dict>
    </array>
</dict>
</plist>'''

def _build_document_wflow(service_sh):
    # User-confirmed working AppleScript logic
    applescript = f'''on run {{input, parameters}}
	repeat with f in input
		set filePath to POSIX path of f
		do shell script quoted form of "{service_sh}" & " " & quoted form of filePath & " > /dev/null 2>&1 &"
	end repeat
	return input
end run'''
    # Escape XML special chars
    escaped = applescript.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>AMApplicationBuild</key>
    <string>523</string>
    <key>AMApplicationVersion</key>
    <string>2.10</string>
    <key>AMWorkflowSchemeVersion</key>
    <string>2.0</string>
    <key>actions</key>
    <array>
        <dict>
            <key>action</key>
            <dict>
                <key>AMAccepts</key>
                <dict>
                    <key>Container</key>
                    <string>List</string>
                    <key>Optional</key>
                    <false/>
                    <key>Types</key>
                    <array>
                        <string>com.apple.cocoa.path</string>
                    </array>
                </dict>
                <key>AMActionVersion</key>
                <string>1.1.1</string>
                <key>AMApplication</key>
                <array>
                    <string>Automator</string>
                </array>
                <key>AMBundleIdentifier</key>
                <string>com.apple.Automator.RunScript</string>
                <key>ActionBundlePath</key>
                <string>/System/Library/Automator/Run AppleScript.action</string>
                <key>ActionName</key>
                <string>Run AppleScript</string>
                <key>ActionParameters</key>
                <dict>
                    <key>source</key>
                    <string>{escaped}</string>
                </dict>
                <key>BundleIdentifier</key>
                <string>com.apple.Automator.RunScript</string>
                <key>CFBundleVersion</key>
                <string>1.1.1</string>
                <key>CanShowSelectedItemsWhenRun</key>
                <false/>
                <key>CanShowWhenRun</key>
                <true/>
                <key>Class Name</key>
                <string>RunScriptAction</string>
                <key>InputUUID</key>
                <string>F73C2C6A-6B0C-4E7B-9E1A-D7E1D8E1D8E1</string>
                <key>Keywords</key>
                <array>
                    <string>Run</string>
                    <string>AppleScript</string>
                </array>
                <key>OutputUUID</key>
                <string>F73C2C6B-6B0C-4E7B-9E1A-D7E1D8E1D8E1</string>
                <key>UUID</key>
                <string>F73C2C6C-6B0C-4E7B-9E1A-D7E1D8E1D8E1</string>
            </dict>
        </dict>
    </array>
    <key>connectors</key>
    <dict/>
    <key>workflowMetaData</key>
    <dict>
        <key>workflowTypeIdentifier</key>
        <string>com.apple.Automator.servicesMenu</string>
    </dict>
</dict>
</plist>'''

def _macos_install():
    wf = _macos_workflow_path()
    contents = wf / "Contents"
    contents.mkdir(parents=True, exist_ok=True)

    # Write Info.plist
    (contents / "Info.plist").write_text(_build_info_plist(), encoding="utf-8")

    # Just call the helper script which covers everything
    service_sh = _HERE / "macos_service.sh"
    shell_script = f'"{service_sh}" "$1"'

    (contents / "document.wflow").write_text(
        _build_document_wflow(shell_script), encoding="utf-8")

    # Refresh Services
    try:
        subprocess.run(["/System/Library/CoreServices/pbs", "-flush"],
                       capture_output=True, timeout=5)
    except Exception:
        pass
    return wf.exists()

def _macos_uninstall():
    wf = _macos_workflow_path()
    if wf.exists(): shutil.rmtree(wf)
    return not wf.exists()

def _macos_check():
    return _macos_workflow_path().exists()


# ═══════════════════════════════════════════════════════════════
#  Windows Registry
# ═══════════════════════════════════════════════════════════════

_WIN_REG_KEY = r"Directory\shell\SnapRename"

def _windows_install():
    try:
        import winreg
    except ImportError:
        return False
    # Use absolute path to the .bat and include --gui
    bat_path = _HERE / f"{_CMD_NAME}.bat"
    # %1 for folders, %V for folder background
    try:
        # 1. Folders
        for base in (_WIN_REG_KEY, r"Drive\shell\SnapRename"):
            cmd = f'"{bat_path}" --gui -d "%1"'
            key = winreg.CreateKeyEx(winreg.HKEY_CLASSES_ROOT, base, 0,
                                     winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, _LABEL)
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, "shell32.dll,3")
            winreg.CloseKey(key)
            cmd_key = winreg.CreateKeyEx(winreg.HKEY_CLASSES_ROOT,
                                          base + r"\command", 0,
                                          winreg.KEY_SET_VALUE)
            winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(cmd_key)
        
        # 2. Folder Background
        bg_base = r"Directory\Background\shell\SnapRename"
        bg_cmd = f'"{bat_path}" --gui -d "%V"'
        key = winreg.CreateKeyEx(winreg.HKEY_CLASSES_ROOT, bg_base, 0,
                                 winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, _LABEL)
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, "shell32.dll,3")
        winreg.CloseKey(key)
        cmd_key = winreg.CreateKeyEx(winreg.HKEY_CLASSES_ROOT,
                                      bg_base + r"\command", 0,
                                      winreg.KEY_SET_VALUE)
        winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, bg_cmd)
        winreg.CloseKey(cmd_key)
        
        return True
    except Exception:
        return False

def _windows_uninstall():
    try:
        import winreg
    except ImportError:
        return False
    for base in (_WIN_REG_KEY, r"Directory\Background\shell\SnapRename", r"Drive\shell\SnapRename"):
        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, base + r"\command")
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, base)
        except Exception:
            pass
    return True

def _windows_check():
    try:
        import winreg
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, _WIN_REG_KEY)
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
#  Linux file managers
# ═══════════════════════════════════════════════════════════════

def _linux_install():
    # Use absolute path for reliability
    cmd = _HERE / _CMD_NAME
    # Ensure command is executable
    if cmd.exists():
        cmd.chmod(0o755)

    # Nautilus
    d = Path.home() / ".local/share/nautilus/scripts"
    d.mkdir(parents=True, exist_ok=True)
    s = d / "Snap Rename"
    # Fix: handle newline-separated paths and spaces safely
    s.write_text(
        f'#!/usr/bin/env bash\n'
        f'# Handle Nautilus selection safely\n'
        f'IFS=$\'\\n\'\n'
        f'for f in $NAUTILUS_SCRIPT_SELECTED_FILE_PATHS; do\n'
        f'    "{cmd}" --gui -d "$f"\n'
        f'    break # Only open the first selected folder for now\n'
        f'done\n', "utf-8")
    s.chmod(0o755)

    # Nemo
    d = Path.home() / ".local/share/nemo/actions"
    d.mkdir(parents=True, exist_ok=True)
    # Fix: quote %f to handle spaces
    (d / "snap_rename.nemo_action").write_text(
        f"[Nemo Action]\nName={_LABEL}\nComment=Open in Snap Rename\n"
        f"Exec=\"{cmd}\" --gui -d \"%f\"\nSelection=any\nExtensions=dir;\nIcon-Name=folder\n", "utf-8")

    # Thunar
    d = Path.home() / ".config/Thunar"
    d.mkdir(parents=True, exist_ok=True)
    uca = d / "uca.xml"
    # Fix: quote %f to handle spaces
    entry = (f'  <action>\n    <icon>folder</icon>\n    <name>{_LABEL}</name>\n'
             f'    <command>"{cmd}" --gui -d "%f"</command>\n    <description>Open in Snap Rename</description>\n'
             f'    <patterns>*</patterns>\n    <directories/>\n  </action>\n')
    if uca.exists():
        text = uca.read_text("utf-8")
        if "Snap Rename" not in text:
            text = text.replace("</actions>", entry + "</actions>")
            uca.write_text(text, "utf-8")
    else:
        uca.write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<actions>\n{entry}</actions>\n', "utf-8")

    # Dolphin
    for d in (Path.home()/".local/share/kio/servicemenus",
              Path.home()/".local/share/kservices5/ServiceMenus"):
        try:
            d.mkdir(parents=True, exist_ok=True)
            # Fix: quote %f to handle spaces
            (d / "snap_rename.desktop").write_text(
                f"[Desktop Entry]\nType=Service\nServiceTypes=KonqPopupMenu/Plugin\n"
                f"MimeType=inode/directory;\nActions=snaprename;\nX-KDE-Submenu={_LABEL}\n\n"
                f"[Desktop Action snaprename]\nName=Open in {_LABEL}\nIcon=folder\n"
                f"Exec=\"{cmd}\" --gui -d \"%f\"\n", "utf-8")
            break
        except Exception:
            continue
    return True

def _linux_uninstall():
    for p in (Path.home()/".local/share/nautilus/scripts/Snap Rename",
              Path.home()/".local/share/nemo/actions/snap_rename.nemo_action"):
        if p.exists(): p.unlink()
    uca = Path.home() / ".config/Thunar/uca.xml"
    if uca.exists():
        text = uca.read_text("utf-8")
        text = re.sub(r'  <action>.*?Snap Rename.*?</action>\n', '', text, flags=re.DOTALL)
        uca.write_text(text, "utf-8")
    for d in (Path.home()/".local/share/kio/servicemenus",
              Path.home()/".local/share/kservices5/ServiceMenus"):
        s = d / "snap_rename.desktop"
        if s.exists(): s.unlink()
    return True

def _linux_check():
    for p in (Path.home()/".local/share/nautilus/scripts/Snap Rename",
              Path.home()/".local/share/nemo/actions/snap_rename.nemo_action",
              Path.home()/".local/share/kio/servicemenus/snap_rename.desktop"):
        if p.exists(): return True
    return False


# ═══════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════

def install():
    msgs = []
    ok_cli, cli_msg = install_cli()
    msgs.append(cli_msg)

    plat = sys.platform
    if plat == "darwin":
        ok_menu = _macos_install()
        msgs.append("   Finder: right-click folder → Quick Actions → Snap Rename")
    elif plat == "win32":
        ok_menu = _windows_install()
        msgs.append("   Explorer: right-click folder → Snap Rename")
    elif plat.startswith("linux"):
        ok_menu = _linux_install()
        msgs.append("   Nautilus/Nemo/Thunar/Dolphin: right-click → Snap Rename")
    else:
        ok_menu = False

    ok = ok_cli or ok_menu
    if ok:
        _MARKER.write_text("installed", encoding="utf-8")
    return ok, "✅ Snap Rename installed!\n" + "\n".join(msgs)

def uninstall():
    uninstall_cli()
    plat = sys.platform
    if plat == "darwin":       _macos_uninstall()
    elif plat == "win32":      _windows_uninstall()
    elif plat.startswith("linux"): _linux_uninstall()
    if _MARKER.exists(): _MARKER.unlink()
    return True, "✅ Snap Rename CLI + context menu uninstalled."

def is_installed():
    if _MARKER.exists(): return True
    plat = sys.platform
    if plat == "darwin":       return _macos_check()
    elif plat == "win32":      return _windows_check()
    elif plat.startswith("linux"): return _linux_check()
    return False

def auto_install_if_needed():
    if is_installed(): return
    ok, msg = install()
    if ok:
        print(f"\n{'='*60}")
        print("  🔀  Snap Rename — First Launch Setup")
        print(f"{'='*60}")
        print(msg)
        print(f"\n  You can now use `{_CMD_NAME}` from any terminal!")
        print(f"  (Restart terminal if needed for PATH changes)")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        ok, msg = uninstall()
        print(msg)
    elif "--check" in sys.argv:
        print("Installed" if is_installed() else "Not installed")
    else:
        ok, msg = install()
        print(msg)
