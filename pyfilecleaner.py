import configparser
import logging
from pathlib import Path
import sys


def setup_logger(config):
    """ログ設定を行う関数"""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    handlers = [logging.StreamHandler(sys.stdout)]  # コンソール出力

    if config.getboolean('Settings', 'enable_logging', fallback=True):
        log_file = config.get('Settings', 'log_filename', fallback='cleanup_log.txt')
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=handlers
    )


def clean_files():
    # 設定ファイルの読み込み
    config = configparser.ConfigParser()
    config_path = Path('config.ini')

    if not config_path.exists():
        print("エラー: config.iniが見つかりません。")
        return

    try:
        # 日本語パスを含むためUTF-8で読み込む
        config.read(config_path, encoding='utf-8')
    except Exception as e:
        print(f"エラー: config.iniの読み込みに失敗しました。UTF-8で保存されていますか？\n詳細: {e}")
        return

    # ロガーの初期化
    setup_logger(config)
    logger = logging.getLogger()

    logger.info("=== クリーンアップ処理を開始します ===")

    # ディレクトリリストの取得（改行で分割してリスト化）
    raw_dirs = config.get('Settings', 'directories', fallback='')
    target_dirs = [d.strip() for d in raw_dirs.split('\n') if d.strip()]

    # 拡張子リストの取得
    raw_exts = config.get('Settings', 'extensions', fallback='')
    target_exts = [e.strip().replace('.', '') for e in raw_exts.split(',') if e.strip()]

    if not target_dirs:
        logger.warning("削除対象のディレクトリが指定されていません。")
        return

    total_deleted = 0
    total_errors = 0

    for dir_str in target_dirs:
        dir_path = Path(dir_str)

        # ディレクトリの存在確認
        if not dir_path.exists():
            logger.warning(f"ディレクトリが見つかりません（スキップ）: {dir_path}")
            continue

        if not dir_path.is_dir():
            logger.warning(f"パスはディレクトリではありません（スキップ）: {dir_path}")
            continue

        logger.info(f"対象フォルダをスキャン中: {dir_path}")

        # 指定された各拡張子についてファイルを検索・削除
        for ext in target_exts:
            # globパターン: *.xlsx, *.xlsm
            files = list(dir_path.glob(f'*.{ext}'))

            if not files:
                continue

            for file_path in files:
                try:
                    file_path.unlink()  # ファイル削除実行
                    logger.info(f"[削除成功] {file_path.name}")
                    total_deleted += 1
                except PermissionError:
                    logger.error(f"[削除失敗] 使用中または権限がありません: {file_path.name}")
                    total_errors += 1
                except Exception as e:
                    logger.error(f"[削除失敗] エラー: {file_path.name} ({e})")
                    total_errors += 1

    logger.info("=== 処理完了 ===")
    logger.info(f"削除数: {total_deleted}, エラー数: {total_errors}")


if __name__ == "__main__":
    clean_files()