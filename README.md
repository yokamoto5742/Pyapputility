# pyapp_update

## 1. 概要
このプログラムは、アプリケーションの更新を自動化するためのGUIツールです。主な機能は以下の通りです：

- 設定ファイル（config.ini）からアプリケーションの更新情報を読み込む
- リアルタイムで進行状況を表示（プログレスバー付き）
- 操作のログを記録（ローテーション機能付き）
- ユーザーフレンドリーなGUIインターフェース

## 2. 主要なクラスと役割

### 2.1 AppConfig（データクラス）
```python
@dataclass
class AppConfig:
    name: str
    delete_dir: str
    copy_src_dir: str
    copy_dest_dir: str
```
- アプリケーションの設定情報を保持する単純なデータ構造
- 各アプリケーションの名前、削除するディレクトリ、コピー元とコピー先のディレクトリを管理

### 2.2 ExcludeInternalFilter
```python
class ExcludeInternalFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "_internal" not in record.getMessage()
```
- ログフィルタークラス
- 内部処理に関するログメッセージ（"_internal"を含む）を除外

### 2.3 ConfigManager
設定ファイルの読み込みと管理を担当するクラス
- **初期化**: config.iniファイルを自動読み込み（UTF-8エンコーディング）
- **ログ保持期間管理**: デフォルト7日間、設定ファイルから変更可能
- **アプリ設定管理**: 各アプリケーションの設定をAppConfigオブジェクトとして保持
- **エラーハンドリング**: 必須キーが不足している場合のエラーログ出力

### 2.4 UpdateManager
実際のファイル操作を行う静的メソッドクラス

#### 主要メソッド：
- **`verify_directories()`**: 必要なディレクトリの存在確認
- **`count_files()`**: ディレクトリ内のファイル数をカウント
- **`delete_files()`**: 指定されたディレクトリ内のファイルとフォルダを再帰的に削除
- **`copy_files()`**: ソースディレクトリから対象ディレクトリにファイルをコピー
- **`update_app()`**: 削除とコピーの処理を順番に実行（メイン処理）

#### 進行状況管理：
- コールバック関数を使用してリアルタイムで進行状況を報告
- 削除処理：20%-60%の進行状況
- コピー処理：60%-95%の進行状況

### 2.5 Application
GUIアプリケーションのメインクラス（tkinterベース）

#### UI構成：
- **アプリ選択コンボボックス**: 設定ファイルから読み込まれたアプリ一覧
- **更新開始ボタン**: 処理開始トリガー
- **プログレスバー**: 処理進行状況の可視化
- **ステータスラベル**: 現在の処理状況メッセージ

#### 処理フロー：
1. アプリ選択 → ボタン有効化
2. 更新開始 → UI無効化、プログレスバー表示
3. バックグラウンド処理実行
4. 完了後UI復旧

## 3. ログ機能の実装

### 3.1 ログ設定の特徴
- **ファイル出力**: `logs/app_updates.log`
- **コンソール出力**: 標準出力にも同時出力
- **ローテーション**: 日次でファイル分割（YYYYMMDD形式）
- **保持期間**: 設定可能（デフォルト7日間）
- **文字エンコーディング**: UTF-8
- **ログレベル**: INFO以上

### 3.2 ログフォーマット
```
YYYY-MM-DD HH:MM:SS,mmm - LEVEL - MESSAGE
```

## 4. エラー処理
プログラム全体で以下のエラーに対する適切な処理が実装されています：

### 4.1 ファイル操作エラー
- **PermissionError**: 権限不足によるアクセス拒否
- **FileNotFoundError**: ファイル・ディレクトリが見つからない
- **OSError**: その他のOS関連エラー

### 4.2 設定エラー
- **KeyError**: 設定ファイルの必須キー不足

### 4.3 エラー時の動作
- 詳細なエラーログの記録
- ユーザーへのエラーメッセージボックス表示
- 処理の安全な中断
- UI状態の適切な復旧

## 5. スレッド処理

### 5.1 マルチスレッド設計
```python
threading.Thread(target=self.run_update, daemon=True).start()
```
- **メインスレッド**: GUI操作とイベント処理
- **ワーカースレッド**: ファイル操作（削除・コピー）
- **スレッド間通信**: `self.after()`メソッドを使用してスレッドセーフな更新

### 5.2 UI応答性の維持
- 長時間のファイル操作中もGUIがフリーズしない
- リアルタイムでの進行状況更新
- 処理中のユーザー操作を適切に制限

## 6. 使用方法

### 6.1 事前準備
1. `config.ini`ファイルに更新したいアプリケーションの情報を設定
2. 必要な権限（削除・書き込み）の確認

### 6.2 実行手順
1. プログラムを起動 → GUIウィンドウが表示
2. ドロップダウンメニューから更新したいアプリケーションを選択
3. 「更新開始」ボタンをクリック
4. 処理の進行状況をプログレスバーで確認
5. 完了メッセージの確認
6. ログファイルで詳細を確認（必要に応じて）

## 7. 設定ファイル（config.ini）の形式

### 7.1 基本構造
```ini
[Logging]
log_retention_days = 7

[App:アプリ名]
DeleteDir = 削除するディレクトリパス
CopySrcDir = コピー元ディレクトリパス
CopyDestDir = コピー先ディレクトリパス
```

### 7.2 設定例
```ini
[Logging]
log_retention_days = 7

[App:sampleapp]
DeleteDir = C:\Shinseikai\sampleapp
CopySrcDir = C:\Shinseikai\Latest_version
CopyDestDir = C:\Shinseikai\sampleapp

```

### 7.3 設定のポイント
- セクション名は`App:`で始める必要がある
- パスはWindowsの絶対パスで指定
- UTF-8エンコーディングで保存

## 8. 特徴的な実装ポイント

### 8.1 型ヒントの活用
```python
def update_app(cls, app_config: AppConfig, 
               progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str]:
```
- Pythonの型ヒントを積極的に使用
- `Optional`, `Dict`, `NoReturn`, `Tuple`, `Callable`などを適切に活用
- コードの可読性と保守性を大幅に向上

### 8.2 データクラスの活用
```python
@dataclass
class AppConfig:
    name: str
    delete_dir: str
    copy_src_dir: str
    copy_dest_dir: str
```
- `@dataclass`デコレータで設定情報を簡潔に管理
- ボイラープレートコードの削減
- 自動的な`__init__`, `__repr__`メソッドの生成

### 8.3 モダンなパス処理
```python
src_path = pathlib.Path(src_dir)
dest_path = pathlib.Path(dest_dir)
```
- `pathlib.Path`を使用したクロスプラットフォーム対応
- 従来の`os.path`より安全で直感的なAPI
- パス操作の型安全性を確保

### 8.4 高度なログ管理
```python
TimedRotatingFileHandler(
    log_file,
    when="midnight",
    interval=1,
    backupCount=config.log_retention_days,
    encoding='utf-8'
)
```
- 日次自動ローテーション
- 古いログファイルの自動削除
- カスタムフィルターによるログ内容の制御

### 8.5 プログレス管理
- コールバック関数パターンでリアルタイム進行状況更新
- ファイル数ベースの正確な進行率計算
- ユーザーフレンドリーな状況表示

## 9. セキュリティ・安全性の考慮

### 9.1 ファイル操作の安全性
- 事前のディレクトリ存在確認
- 権限エラーの適切なハンドリング
- トランザクション的な処理（削除→コピーの順序）

### 9.2 エラー処理の徹底
- 各ファイル操作での個別エラーハンドリング
- 詳細なエラーログ記録
- 処理の安全な中断機能

### 9.3 設定ファイルの安全性
- UTF-8エンコーディングの明示的指定
- 必須設定項目の検証
- 設定エラー時の適切なログ出力

## 10. システム要件

### 10.1 必要な環境
- **OS**: Windows10以上(32ビットに対応)
- **Python**: 3.10以上（データクラス、型ヒント対応）
- **標準ライブラリ**: configparser, logging, os, pathlib, shutil, threading, tkinter

### 10.2 実行に必要な権限
- 削除対象ディレクトリへの書き込み・削除権限
- コピー元ディレクトリへの読み取り権限
- コピー先ディレクトリへの書き込み権限
- ログディレクトリの作成権限

## 11. トラブルシューティング

### 11.1 よくある問題
1. **PermissionError**: 管理者権限で実行、またはファイルの使用状況を確認
2. **FileNotFoundError**: config.iniのパス設定を確認
3. **GUI表示されない**: tkinterの正常なインストールを確認

### 11.2 ログの確認
- `logs/app_updates.log`で詳細なエラー情報を確認
- エラーの種類と発生箇所を特定してトラブルシューティング
