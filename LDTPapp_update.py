import os
import shutil
import configparser
import logging
from logging.handlers import TimedRotatingFileHandler
import tkinter as tk
from tkinter import ttk
import threading


class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini', encoding='utf-8')
        self.delete_dir = self.config['Directories']['DeleteDir']
        self.copy_src_dir = self.config['Directories']['CopySrcDir']
        self.copy_dest_dir = self.config['Directories']['CopyDestDir']
        self.log_retention_days = self.config.getint('Logging', 'log_retention_days', fallback=7)


class ExcludeInternalFilter(logging.Filter):
    def filter(self, record):
        return "_internal" not in record.getMessage()


def setup_logging(config):
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "file_operations.log")
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=config.log_retention_days,
        encoding='utf-8'
    )
    file_handler.suffix = "%Y%m%d"

    console_handler = logging.StreamHandler()

    exclude_internal_filter = ExcludeInternalFilter()
    file_handler.addFilter(exclude_internal_filter)
    console_handler.addFilter(exclude_internal_filter)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            file_handler,
            console_handler
        ]
    )


def delete_files(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in files:
            file_path = os.path.join(root, name)
            try:
                os.unlink(file_path)
                logging.info(f"ファイルを削除しました: {file_path}")
            except Exception as e:
                logging.error(f"ファイルの削除に失敗しました: {file_path}. エラー: {e}")

        for name in dirs:
            dir_path = os.path.join(root, name)
            try:
                os.rmdir(dir_path)
                logging.info(f"ディレクトリを削除しました: {dir_path}")
            except Exception as e:
                logging.error(f"ディレクトリの削除に失敗しました: {dir_path}. エラー: {e}")


def copy_files(src_dir, dest_dir):
    try:
        shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True, copy_function=shutil.copy2)
        logging.info(f"ファイルをコピーしました: {src_dir} から {dest_dir} へ")
    except Exception as e:
        logging.error(f"ファイルのコピーに失敗しました: {src_dir} から {dest_dir} へ. エラー: {e}")


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LDTPapp Update")
        self.geometry("300x100")
        self.label = ttk.Label(self, text="Updateを実行中")
        self.label.pack(pady=20)
        self.progress = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=200, mode='indeterminate')
        self.progress.pack(pady=10)

    def start_update(self):
        self.progress.start()
        threading.Thread(target=self.run_update, daemon=True).start()

    def run_update(self):
        try:
            config = Config()
            setup_logging(config)
            logging.info("LDTPappのupdateを開始します")

            logging.info(f"削除を開始: {config.delete_dir}")
            delete_files(config.delete_dir)
            logging.info("削除完了")

            logging.info(f"コピーを開始: {config.copy_src_dir} から {config.copy_dest_dir} へ")
            copy_files(config.copy_src_dir, config.copy_dest_dir)
            logging.info("コピー完了")

        except configparser.Error as e:
            logging.error(f"設定ファイルの読み込みに失敗しました: {e}")
        except Exception as e:
            logging.error(f"予期せぬエラーが発生しました: {e}")

        logging.info("LDTPappのupdateを完了しました")
        self.after(0, self.update_completed)

    def update_completed(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.label.config(text="LDTPappのupdateを完了しました")
        self.geometry("300x70")  # ウィンドウサイズを調整
        self.after(1500, self.close_application)

    def close_application(self):
        self.destroy()


def main():
    app = Application()
    app.after(0, app.start_update)
    app.mainloop()


if __name__ == "__main__":
    main()
