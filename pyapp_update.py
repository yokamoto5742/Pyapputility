import configparser
import logging
import os
import pathlib
import shutil
import threading
import tkinter as tk
from dataclasses import dataclass
from logging.handlers import TimedRotatingFileHandler
from tkinter import messagebox, ttk
from typing import Dict, NoReturn, Optional, Tuple, Callable


@dataclass
class AppConfig:
    name: str
    delete_dir: str
    copy_src_dir: str
    copy_dest_dir: str


class ExcludeInternalFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "_internal" not in record.getMessage()


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


class UpdateManager:
    @staticmethod
    def verify_directories(app_config: AppConfig) -> Tuple[bool, str]:
        if not pathlib.Path(app_config.copy_src_dir).exists():
            return False, f"コピー元ディレクトリが見つかりません: {app_config.copy_src_dir}"

        if not pathlib.Path(app_config.delete_dir).exists():
            return False, f"削除対象ディレクトリが見つかりません: {app_config.delete_dir}"

        copy_dest_parent = pathlib.Path(app_config.copy_dest_dir).parent
        if not copy_dest_parent.exists():
            return False, f"コピー先の親ディレクトリが見つかりません: {copy_dest_parent}"

        return True, ""

    @staticmethod
    def count_files(directory: str) -> int:
        count = 0
        for root, dirs, files in os.walk(directory):
            count += len(files)
        return count

    @staticmethod
    def delete_files(directory: str, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> None:
        total_files = UpdateManager.count_files(directory)
        processed_files = 0

        for root, dirs, files in os.walk(directory, topdown=False):
            for name in files:
                file_path = pathlib.Path(root) / name
                try:
                    file_path.unlink()
                    logging.info(f"ファイルを削除しました: {file_path}")
                    processed_files += 1
                    if progress_callback:
                        progress_callback(processed_files, total_files, f"削除中: {name}")
                except PermissionError:
                    logging.error(f"権限エラー: {file_path}の削除ができません")
                except FileNotFoundError:
                    logging.warning(f"ファイルが見つかりません: {file_path}")
                except OSError as e:
                    logging.error(f"ファイルの削除に失敗しました: {file_path}. エラー: {e}")

            for name in dirs:
                dir_path = pathlib.Path(root) / name
                try:
                    dir_path.rmdir()
                    logging.info(f"ディレクトリを削除しました: {dir_path}")
                except PermissionError:
                    logging.error(f"権限エラー: {dir_path}の削除ができません")
                except OSError as e:
                    logging.error(f"ディレクトリの削除に失敗しました: {dir_path}. エラー: {e}")

    @staticmethod
    def copy_files(src_dir: str, dest_dir: str,
                   progress_callback: Optional[Callable[[int, int, str], None]] = None) -> None:
        src_path = pathlib.Path(src_dir)
        dest_path = pathlib.Path(dest_dir)

        total_files = UpdateManager.count_files(src_dir)
        processed_files = 0

        try:
            dest_path.mkdir(parents=True, exist_ok=True)

            # ファイルを一つずつコピー
            for root, dirs, files in os.walk(src_dir):
                # 相対パスを計算
                rel_root = pathlib.Path(root).relative_to(src_path)
                dest_root = dest_path / rel_root

                dest_root.mkdir(parents=True, exist_ok=True)

                for file in files:
                    src_file = pathlib.Path(root) / file
                    dest_file = dest_root / file

                    try:
                        shutil.copy2(src_file, dest_file)
                        processed_files += 1
                        if progress_callback:
                            progress_callback(processed_files, total_files, f"コピー中: {file}")
                        logging.info(f"ファイルをコピーしました: {src_file} -> {dest_file}")
                    except Exception as e:
                        logging.error(f"ファイルのコピーに失敗: {src_file} -> {dest_file}. エラー: {e}")

        except PermissionError:
            logging.error(f"権限エラー: {src_dir}から{dest_dir}へのコピーができません")
        except FileNotFoundError:
            logging.error(f"ディレクトリが見つかりません: {src_dir}または{dest_dir}")
        except Exception as e:
            logging.error(f"ファイルのコピーに失敗しました: {src_dir}から{dest_dir}へ. エラー: {e}")

    @classmethod
    def update_app(cls, app_config: AppConfig, progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[
        bool, str]:
        logging.info(f"{app_config.name}のアップデートを開始します")

        if progress_callback:
            progress_callback(10, "ディレクトリを確認中...")

        dirs_exist, error_msg = cls.verify_directories(app_config)
        if not dirs_exist:
            logging.error(error_msg)
            return False, error_msg

        try:
            if progress_callback:
                progress_callback(20, "削除を開始中...")

            logging.info(f"削除を開始: {app_config.delete_dir}")

            def delete_progress(current, total, filename):
                if progress_callback:
                    percent = 20 + int((current / total) * 40)  # 20%から60%まで
                    progress_callback(percent, f"現在{percent}%完了")

            cls.delete_files(app_config.delete_dir, delete_progress)
            logging.info("削除完了")

            if progress_callback:
                progress_callback(60, "コピーを開始中...")

            logging.info(f"コピーを開始: {app_config.copy_src_dir}から{app_config.copy_dest_dir}へ")

            def copy_progress(current, total, filename):
                if progress_callback:
                    percent = 60 + int((current / total) * 35)  # 60%から95%まで
                    progress_callback(percent, f"現在{percent}%完了")

            cls.copy_files(app_config.copy_src_dir, app_config.copy_dest_dir, copy_progress)
            logging.info("コピー完了")

            if progress_callback:
                progress_callback(100, "更新完了")

            logging.info(f"{app_config.name}のアップデートが完了しました")
            return True, "更新が完了しました"
        except Exception as e:
            error_msg = f"更新処理中にエラーが発生しました: {str(e)}"
            logging.error(error_msg)
            return False, error_msg


class Application(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("pyapp_update")
        self.geometry("300x250")
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

        self.progress = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=300)

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
        self.progress['value'] = 0

        threading.Thread(target=self.run_update, daemon=True).start()

    def update_progress(self, value: int, message: str) -> None:
        self.progress['value'] = value
        self.status_label.config(text=message)

    def run_update(self) -> None:
        try:
            setup_logging(self.config_manager)
            app_config = self.config_manager.apps[self.selected_app]

            def progress_callback(percent: int, message: str):
                self.after(0, self.update_progress, percent, message)

            success, message = UpdateManager.update_app(app_config, progress_callback)
            self.after(0, self.update_completed, success, message)
        except Exception as e:
            logging.error(f"更新中にエラーが発生しました: {e}")
            self.after(0, self.update_completed, False, str(e))

    def update_completed(self, success: bool, message: str) -> None:
        self.progress.pack_forget()

        if success:
            self.status_label.config(text=f"{self.selected_app}の更新が完了しました")
            self.after(1500, self.reset_ui)
        else:
            messagebox.showerror("エラー", f"更新に失敗しました: {message}")
            self.reset_ui()

    def reset_ui(self) -> None:
        self.app_combo.config(state="readonly")
        self.selected_app = None
        self.app_combo.set('')
        self.update_button.config(state="disabled")
        self.status_label.config(text="更新するアプリを選択してください")


def setup_logging(config: ConfigManager) -> None:
    log_dir = pathlib.Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "app_updates.log"
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", backupCount=config.log_retention_days,
                                            encoding='utf-8')
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


def main() -> NoReturn:
    app = Application()
    app.mainloop()


if __name__ == "__main__":
    main()
