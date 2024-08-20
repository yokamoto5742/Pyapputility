import shutil
import os
import sys
import datetime
import configparser
from urllib.parse import urlparse
import glob


def get_config_path():
    if getattr(sys, 'frozen', False):
        # 実行可能ファイルとして実行されている場合
        return os.path.join(os.path.dirname(sys.executable), 'config.ini')
    else:
        # 通常のPythonスクリプトとして実行されている場合
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')


# 設定ファイルの読み込み
config = configparser.ConfigParser()
config.read(get_config_path())

# データベースURLとアプリケーションディレクトリの取得
db_url = config['Database']['db_url']
app_dir = config['Paths']['app_dir']

# URLからデータベースファイル名を抽出
db_file = urlparse(db_url).path.strip('/')

# バックアップ元のデータベースファイルパスを構築
src_db = os.path.join(app_dir, db_file)

# バックアップ先のディレクトリ
backup_dir = config['Paths']['backup_dir']

# バックアップの保持期間を設定ファイルから取得（デフォルトは10日）
retention_days = config.getint('Backup', 'retention_days', fallback=10)

# 現在の日時を取得してファイル名に使用
current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
dst_db = os.path.join(backup_dir, f"backup_{current_time}.db")

# バックアップ先ディレクトリが存在しない場合は作成
os.makedirs(backup_dir, exist_ok=True)

# バックアップを実行
shutil.copy2(src_db, dst_db)

# 設定された日数以上前のバックアップファイルを削除
current_date = datetime.datetime.now()
for backup_file in glob.glob(os.path.join(backup_dir, "backup_*.db")):
    file_date_str = os.path.basename(backup_file).split("_")[1].split(".")[0]
    file_date = datetime.datetime.strptime(file_date_str, "%Y%m%d")
    if (current_date - file_date).days > retention_days:
        os.remove(backup_file)

print(f"バックアップが完了しました: {dst_db}")
print(f"{retention_days}日以上前の古いバックアップファイルを削除しました。")
