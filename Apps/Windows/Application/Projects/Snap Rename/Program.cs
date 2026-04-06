using System;
using System.Diagnostics;
using System.IO;

class Program
{
    static void Main(string[] args)
    {
        try
        {
            string exeDir = AppContext.BaseDirectory;
            string scriptPath = Path.Combine(exeDir, "main.py");

            if (!File.Exists(scriptPath))
                return;

            Process.Start(new ProcessStartInfo
            {
                FileName = "pythonw",
                Arguments = $"\"{scriptPath}\" --gui",
                WorkingDirectory = exeDir,
                UseShellExecute = true,
                Verb = "runas"
            });
        }
        catch { }
    }
}