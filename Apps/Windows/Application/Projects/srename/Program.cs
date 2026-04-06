using System;
using System.Diagnostics;
using System.IO;
using System.Linq;

class Program
{
    static void Main(string[] args)
    {
        try
        {
            string exeDir = AppContext.BaseDirectory;
            string scriptPath = Path.Combine(exeDir, "main.py");

            if (!File.Exists(scriptPath))
            {
                Console.WriteLine("Error: main.py not found.");
                return;
            }

            string userArgs = string.Join(" ", args.Select(a => $"\"{a}\""));

            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = "python",
                Arguments = $"\"{scriptPath}\" {userArgs}",
                WorkingDirectory = exeDir,

                UseShellExecute = true,
                Verb = "runas",
                RedirectStandardInput = false,
                RedirectStandardOutput = false,
                RedirectStandardError = false
            };

            var process = Process.Start(psi);

            process.WaitForExit(); // 👈 THIS IS KEY
        }
        catch (Exception ex)
        {
            Console.WriteLine("Error:");
            Console.WriteLine(ex.Message);
        }
    }
}