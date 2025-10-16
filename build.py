import subprocess
import shutil


def build_executable():
    subprocess.run([
        "pyinstaller",
        "--name=pyapp_update",
        "--windowed",
        "pyapp_update.py"
    ])

    shutil.copy("config.ini", "dist/config.ini")


if __name__ == "__main__":
    build_executable()
