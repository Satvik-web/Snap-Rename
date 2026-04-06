using System;
using System.IO;
using System.Net.Http;
using System.IO.Compression;
using System.Diagnostics;
using System.Security.Principal;
using Microsoft.Win32;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        Console.Title = "Snap Rename Installer";

        EnsureAdmin();

        string python = CheckPython();
        if (python == null) return;

        Step(2, "Upgrading pip", RunProcess(python, "-m pip install --upgrade pip"));
        Step(2, "Installing dependencies (pyqt6, textual)", RunProcess(python, "-m pip install pyqt6 textual"));

        Step(3, "Downloading & installing Snap Rename", await DownloadAndExtract());

        Step(4, "Setting up CLI (srename)", SetupCLI());
        Step(4, "Adding Explorer right-click menu", SetupContextMenu());

        Step(5, "Creating Start Menu shortcut", CopyShortcuts());

        Console.ForegroundColor = ConsoleColor.Green;
        Console.WriteLine("\n✅ Installation Complete!");
        Console.ResetColor();

        Console.Write("\nRun Snap Rename now? (Y/N): ");
        var input = Console.ReadLine()?.Trim().ToLower();

        if (input == "y" || input == "yes")
        {
            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = @"C:\Program Files\Snap Rename\Snap Rename.exe",
                    UseShellExecute = true
                });
            }
            catch
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("❌ Failed to launch Snap Rename.");
                Console.ResetColor();
            }
        }
    }

    // ─────────────────────────────────────────────
    // UAC Elevation
    // ─────────────────────────────────────────────
    static void EnsureAdmin()
    {
        var identity = WindowsIdentity.GetCurrent();
        var principal = new WindowsPrincipal(identity);

        if (!principal.IsInRole(WindowsBuiltInRole.Administrator))
        {
            var exe = Process.GetCurrentProcess().MainModule.FileName;

            var psi = new ProcessStartInfo
            {
                FileName = exe,
                UseShellExecute = true,
                Verb = "runas"
            };

            try { Process.Start(psi); }
            catch
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("X Administrator permission required.");
                Console.ResetColor();
            }

            Environment.Exit(0);
        }
    }

    // ─────────────────────────────────────────────
    // Step UI
    // ─────────────────────────────────────────────
    static void Step(int step, string text, bool success)
    {
        Console.ForegroundColor = success ? ConsoleColor.Green : ConsoleColor.Red;
        Console.WriteLine($"[{step}/5] {text}");
        Console.ResetColor();
    }

    static void Fail(string msg)
    {
        Console.ForegroundColor = ConsoleColor.Red;
        Console.WriteLine($"❌ {msg}");
        Console.ResetColor();
    }

    // ─────────────────────────────────────────────
    // 1. Python Check
    // ─────────────────────────────────────────────
    static string CheckPython()
    {
        Console.WriteLine("[1/5] Checking Python...");

        try
        {
            var p = Process.Start(new ProcessStartInfo
            {
                FileName = "python",
                Arguments = "--version",
                RedirectStandardOutput = true,
                UseShellExecute = false
            });

            p.WaitForExit();

            if (p.ExitCode == 0)
            {
                Console.ForegroundColor = ConsoleColor.Green;
                Console.WriteLine("Python detected");
                Console.ResetColor();
                return "python";
            }
        }
        catch { }

        Fail("Python not found.");
        Console.WriteLine("\nInstall Python: https://www.python.org/downloads/");
        Console.WriteLine("IMPORTANT: Check 'Add Python to PATH'\n");
        return null;
    }

    // ─────────────────────────────────────────────
    // Run process
    // ─────────────────────────────────────────────
    static bool RunProcess(string file, string args)
    {
        try
        {
            var p = Process.Start(new ProcessStartInfo
            {
                FileName = file,
                Arguments = args,
                UseShellExecute = false
            });

            p.WaitForExit();
            return p.ExitCode == 0;
        }
        catch { return false; }
    }

    // ─────────────────────────────────────────────
    // 3. Download & Extract
    // ─────────────────────────────────────────────
    static async Task<bool> DownloadAndExtract()
    {
        try
        {
            string zipPath = Path.Combine(Path.GetTempPath(), "snaprename.zip");
            string installPath = @"C:\Program Files\Snap Rename";

            using var client = new HttpClient();
            var bytes = await client.GetByteArrayAsync(
                "https://github.com/Satvik-web/Snap-Rename/releases/download/v1.0.0/windows_app.zip"
            );

            await File.WriteAllBytesAsync(zipPath, bytes);

            if (Directory.Exists(installPath))
                Directory.Delete(installPath, true);

            ZipFile.ExtractToDirectory(zipPath, installPath);

            return true;
        }
        catch
        {
            return false;
        }
    }

    // ─────────────────────────────────────────────
    // 4. CLI setup
    // ─────────────────────────────────────────────
    static bool SetupCLI()
    {
        try
        {
            string dir = @"C:\Program Files\Snap Rename";

            string path = Environment.GetEnvironmentVariable("PATH", EnvironmentVariableTarget.Machine);

            if (!path.Contains(dir))
            {
                Environment.SetEnvironmentVariable(
                    "PATH",
                    path + ";" + dir,
                    EnvironmentVariableTarget.Machine
                );
            }

            return true;
        }
        catch { return false; }
    }

    // ─────────────────────────────────────────────
    // Context Menu
    // ─────────────────────────────────────────────
    static bool SetupContextMenu()
    {
        try
        {
            using var key = Registry.ClassesRoot.CreateSubKey(@"Directory\shell\Snap Rename");
            key.SetValue("", "Snap Rename");
            key.SetValue("Icon", @"C:\Program Files\Snap Rename\logo.ico");

            using var cmd = key.CreateSubKey("command");
            cmd.SetValue("", "\"C:\\Program Files\\Snap Rename\\srename.exe\" --gui -d \"%1\"");

            return true;
        }
        catch { return false; }
    }

    // ─────────────────────────────────────────────
    // 5. Start Menu Shortcut
    // ─────────────────────────────────────────────
    static bool CopyShortcuts()
    {
        try
        {
            string installDir = @"C:\Program Files\Snap Rename";
            string sourceShortcut = Path.Combine(installDir, "Snap Rename.lnk");

            string startMenu = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.StartMenu),
                "Programs",
                "Snap Rename.lnk"
            );

            string desktop = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.Desktop),
                "Snap Rename.lnk"
            );

            File.Copy(sourceShortcut, startMenu, true);
            File.Copy(sourceShortcut, desktop, true);

            return true;
        }
        catch
        {
            return false;
        }
    }
}