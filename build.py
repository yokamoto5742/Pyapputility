import subprocess
import shutil


def build_executable():
    subprocess.run([
        "pyinstaller",
        "--name=file_move",
        "--windowed",
        "LDTPapp_update.py"
    ])

    # 必要なファイルをdistフォルダにコピー
    shutil.copy("config.ini", "dist/config.ini")


if __name__ == "__main__":
    build_executable()
