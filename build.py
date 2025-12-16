import subprocess

def build_executable():
    subprocess.run([
        "pyinstaller",
        "--name=pyfilecleaner",
        "--windowed",
        "--onefile",
        "--add-data", "config.ini;.",
        "pyfilecleaner.py"
    ])


if __name__ == "__main__":
    build_executable()
