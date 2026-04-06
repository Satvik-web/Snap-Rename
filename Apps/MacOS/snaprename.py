import os
import subprocess
import sys


def get_python_path():
    config = os.path.expanduser("~/.srenameinfo")

    if os.path.exists(config):
        with open(config) as f:
            python = f.read().strip()
            if os.path.exists(python):
                return python

    # If config missing or invalid → fail clearly
    print("❌ Python path not found or invalid (~/.srenameinfo)")
    print("👉 Please run the installer again.")
    sys.exit(1)


def get_resource_path():
    # Inside .app → go to Resources folder
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(base_path, "..", "Resources"))


def main():
    python = get_python_path()
    resources = get_resource_path()
    main_script = os.path.join(resources, "main.py")

    if not os.path.exists(main_script):
        print("❌ main.py not found inside app bundle")
        sys.exit(1)

    # Change working directory to Resources
    os.chdir(resources)

    # Launch GUI
    subprocess.Popen([
        python,
        main_script,
        "--gui"
    ])


if __name__ == "__main__":
    main()