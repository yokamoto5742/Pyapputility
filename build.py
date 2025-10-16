import subprocess

def build_executable():
    subprocess.run([
        "pyinstaller",
        "--name=pyapp_update",
        "--windowed",
        "--add-data", "config.ini;.",
        "pyapp_update.py"
    ])


if __name__ == "__main__":
    build_executable()
