import subprocess
import shutil


def build_executable():
    subprocess.run([
        "pyinstaller",
        "--name=pyapp_update",
        "--windowed",
        "--add-data", "utils/config.ini;.",
        "pyapp_update.py"
    ])


if __name__ == "__main__":
    build_executable()
