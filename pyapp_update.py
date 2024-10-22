import os
import shutil
import configparser
import logging
from logging.handlers import TimedRotatingFileHandler
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Dict, Optional, NoReturn
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    name: str
    delete_dir: str
    copy_src_dir: str
    copy_dest_dir: str


class ConfigManager:
    def __init__(self) -> None:
        self.config = configparser.ConfigParser()
        self.config.read('config.ini', encoding='utf-8')
        self.apps: Dict[str, AppConfig] = {}
        self.log_retention_days: int = self.config.getint(
            'Logging',
            'log_retention_days',
            fallback=7
        )
        self._load_apps()

    def _load_apps(self) -> None:
        for section in self.config.sections():
            if not section.startswith('App:'):
                continue
            app_name = section.split(':', 1)[1]
            try:
                self.apps[app_name] = AppConfig(
                    name=app_name,
                    delete_dir=self.config[section]['DeleteDir'],
                    copy_src_dir=self.config[section]['CopySrcDir'],
                    copy_dest_dir=self.config[section]['CopyDestDir']
                )
            except KeyError as e:
                logging.error(f"Config section {section} is missing required key: {e}")


class ExcludeInternalFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "_internal" not in record.getMessage()


def setup_logging(config: ConfigManager) -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "app_updates.log"
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

    for handler in (file_handler, console_handler):
        handler.addFilter(exclude_internal_filter)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[file_handler, console_handler]
    )


class UpdateManager:
    @staticmethod
    def delete_files(directory: str) -> None:
        for root, dirs, files in os.walk(directory, topdown=False):
            for name in files:
                file_path = Path(root) / name
                try:
                    file_path.unlink()
                    logging.info(f"ファイルを削除しました: {file_path}")
                except PermissionError:
                    logging.error(f"権限エラー: {file_path}の削除ができません")
                except FileNotFoundError:
                    logging.warning(f"ファイルが見つかりません: {file_path}")
                except OSError as e:
                    logging.error(f"ファイルの削除に失敗しました: {file_path}. エラー: {e}")

            for name in dirs:
                dir_path = Path(root) / name
                try:
                    dir_path.rmdir()
                    logging.info(f"ディレクトリを削除しました: {dir_path}")
                except PermissionError:
                    logging.error(f"権限エラー: {dir_path}の削除ができません")
                except OSError as e:
                    logging.error(f"ディレクトリの削除に失敗しました: {dir_path}. エラー: {e}")

    @staticmethod
    def copy_files(src_dir: str, dest_dir: str) -> None:
        try:
            shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True, copy_function=shutil.copy2)
            logging.info(f"ファイルをコピーしました: {src_dir} から {dest_dir} へ")
        except PermissionError:
            logging.error(f"権限エラー: {src_dir}から{dest_dir}へのコピーができません")
        except FileNotFoundError:
            logging.error(f"ディレクトリが見つかりません: {src_dir}または{dest_dir}")
        except shutil.Error as e:
            logging.error(f"ファイルのコピーに失敗しました: {src_dir}から{dest_dir}へ. エラー: {e}")

    @classmethod
    def update_app(cls, app_config: AppConfig) -> None:
        logging.info(f"{app_config.name}のアップデートを開始します")

        logging.info(f"削除を開始: {app_config.delete_dir}")
        cls.delete_files(app_config.delete_dir)
        logging.info("削除完了")

        logging.info(f"コピーを開始: {app_config.copy_src_dir}から{app_config.copy_dest_dir}へ")
        cls.copy_files(app_config.copy_src_dir, app_config.copy_dest_dir)
        logging.info("コピー完了")

        logging.info(f"{app_config.name}のアップデートが完了しました")


class Application(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("pyapp_update")
        self.geometry("300x200")
        self.config_manager = ConfigManager()
        self.selected_app: Optional[str] = None
        self.setup_ui()

    def setup_ui(self) -> None:
        select_frame = ttk.Frame(self)
        select_frame.pack(pady=20)

        ttk.Label(select_frame, text="アプリ選択:").pack(side=tk.LEFT, padx=5)
        self.app_combo = ttk.Combobox(
            select_frame,
            values=list(self.config_manager.apps.keys()),
            state="readonly"
        )
        self.app_combo.pack(side=tk.LEFT, padx=5)
        self.app_combo.bind('<<ComboboxSelected>>', self.on_app_selected)

        self.update_button = ttk.Button(
            self,
            text="更新開始",
            command=self.start_update,
            state="disabled"
        )
        self.update_button.pack(pady=10)

        self.progress = ttk.Progressbar(
            self,
            orient=tk.HORIZONTAL,
            length=300,
            mode='indeterminate'
        )

        self.status_label = ttk.Label(self, text="更新するアプリを選択してください")
        self.status_label.pack(pady=20)

    def on_app_selected(self, event: tk.Event) -> None:
        self.selected_app = self.app_combo.get()
        self.update_button.config(state="normal")
        self.status_label.config(text=f"{self.selected_app}を選択しました")

    def start_update(self) -> None:
        if not self.selected_app:
            return

        self.update_button.config(state="disabled")
        self.app_combo.config(state="disabled")
        self.status_label.config(text=f"{self.selected_app}を更新中...")
        self.progress.pack(pady=10)
        self.progress.start()

        threading.Thread(target=self.run_update, daemon=True).start()

    def run_update(self) -> None:
        try:
            setup_logging(self.config_manager)
            app_config = self.config_manager.apps[self.selected_app]
            UpdateManager.update_app(app_config)
            self.after(0, self.update_completed, True)
        except KeyError:
            logging.error("アプリ設定が見つかりません")
            self.after(0, self.update_completed, False)
        except Exception as e:
            logging.error(f"更新中にエラーが発生しました: {e}")
            self.after(0, self.update_completed, False)

    def update_completed(self, success: bool) -> None:
        self.progress.stop()
        self.progress.pack_forget()

        if success:
            self.status_label.config(text=f"{self.selected_app}の更新が完了しました")
            self.after(1500, self.reset_ui)
        else:
            messagebox.showerror("エラー", "更新中にエラーが発生しました。ログを確認してください。")
            self.reset_ui()

    def reset_ui(self) -> None:
        self.app_combo.config(state="readonly")
        self.selected_app = None
        self.app_combo.set('')
        self.update_button.config(state="disabled")
        self.status_label.config(text="更新するアプリを選択してください")


def main() -> NoReturn:
    app = Application()
    app.mainloop()


if __name__ == "__main__":
    main()
