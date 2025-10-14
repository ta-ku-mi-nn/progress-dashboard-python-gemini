# メンテナンス用ドキュメント

## 目次

- 概要  
- プロジェクト構成
- 各フォルダの詳細説明  ←★追加
- フォルダに属しない主なファイルの説明 ←★追加
- 主要ファイル解説
- データベーススキーマ
- メンテナンスガイド

---

## 概要

本ドキュメントは、学習進捗ダッシュボードアプリケーションの保守・機能追加を円滑に行うための手引きです。  
全体構成、各ファイルの役割、よくある作業手順をまとめています。

---

## プロジェクト構成

本アプリはDashフレームワークを用いたWebアプリケーションで、生徒の学習進捗を可視化・管理します。  
データはSQLiteで永続化されます。

```
/ (プロジェクトルート)
├─ auth/         # 認証・ユーザー管理
├─ callbacks/    # Dashコールバック（動的な振る舞い）
├─ charts/       # グラフ生成
├─ components/   # UI部品（レイアウト・モーダル等）
├─ config/       # 設定・スタイル
├─ data/         # データ処理（DBアクセス等）
├─ utils/        # 補助ツール（PDF生成等）
├─ app_main.py   # アプリのエントリーポイント
├─ initialize_database.py # DB初期化スクリプト
├─ progress.db   # SQLiteデータベース
├─ requirements.txt # 依存ライブラリ
├─ text_data.csv # 参考書マスターデータ
├─ bulk_buttons.json # 一括登録ボタン設定
└─ .gitignore    # Git除外設定
```

---

## 各フォルダの詳細説明

### auth/
- **役割:** ユーザー認証・管理、セッション管理を担当。
- **主なファイル例:**
  - `auth_utils.py`: パスワードハッシュ化や認証ロジック
  - `session_manager.py`: セッションの生成・検証
  - `user_manager.py`: ユーザー情報のCRUD
  - `users.db`: 認証用DB

### callbacks/
- **役割:** Dashアプリの動的な振る舞い（コールバック）を機能ごとに分割管理。
- **主なファイル例:**
  - `main_callbacks.py`: 全体レイアウトやページ切替
  - `auth_callbacks.py`: ログイン・ログアウト処理
  - `progress_callbacks.py`: 進捗グラフ・テーブル表示
  - `admin_callbacks.py`, `homework_callbacks.py`など: 各機能ごと

### charts/
- **役割:** グラフやチャートの生成ロジックを集約。
- **主なファイル例:**
  - `chart_generator.py`: 進捗棒グラフ等の生成
  - `generator.py`: 汎用グラフ生成

### components/
- **役割:** UI部品（レイアウト、モーダル、ナビバー等）の再利用可能なパーツを管理。
- **主なファイル例:**
  - `main_layout.py`: 全体レイアウト・ナビゲーション
  - `modals.py`: モーダルウィンドウ
  - `login_components.py`: ログイン画面部品

### config/
- **役割:** アプリの設定値やスタイル定義を管理。
- **主なファイル例:**
  - `settings.py`: ポート番号や環境設定
  - `styles.py`: CSSや外部スタイル

### data/
- **役割:** データベースとのやり取りやデータ加工処理を担当。
- **主なファイル例:**
  - `nested_json_processor.py`: 生徒・進捗・宿題等のCRUD

### utils/
- **役割:** PDF生成や権限管理など、補助的なユーティリティ関数を集約。- **主なファイル例:**
  - `dashboard_pdf.py`, `pdf_export.py`: PDF出力
  - `permissions.py`: 権限チェック

---

## フォルダに属しない主なファイルの説明

- **app_main.py**  
  アプリケーションのエントリーポイント。Dashインスタンス生成、全体レイアウト、ルーティング、コールバック登録などアプリの中枢を担う。

- **initialize_database.py**  
  データベース（progress.db）を初期化し、CSVやJSONから初期データを投入するスクリプト。

- **update_database_schema.py**  
  データベーススキーマのバージョンアップやマイグレーションを行うスクリプト。

- **progress.db**  
  SQLite形式のアプリケーションデータベース本体。

- **requirements.txt**  
  必要なPythonライブラリ一覧。pipで一括インストール可能。

- **text_data.csv**  
  参考書マスターデータ。初期投入やマスタ更新時に利用。

- **bulk_buttons.json**  
  一括登録ボタンの初期設定データ。

- **.gitignore**  
  Gitで追跡しないファイル・フォルダのパターンを定義。

---

### データベーススキーマ (progress.db)
主要なテーブルとその役割は以下の通りです。

users: ユーザー情報（講師、管理者）

students: 生徒情報

student_instructors: 生徒と講師の関連付け

master_textbooks: 参考書のマスターデータ

progress: 生徒ごとの参考書の進捗状況

homework: 生徒ごとの宿題

past_exam_results: 過去問の成績

bug_reports: 不具合報告

changelog: アプリケーションの更新履歴

## メンテナンスガイド
### 新しいページを追加する
レイアウト作成: components/ディレクトリに、新しいページのレイアウトを生成する関数（例: create_new_page_layout）をnew_page_layout.pyとして作成します。

コールバック作成: callbacks/ディレクトリに、そのページの動的な処理を記述するnew_page_callbacks.pyを作成し、register_new_page_callbacks関数を定義します。

ルーティング設定: app_main.pyのdisplay_page関数に、新しいURLパス（例: /new-page）と、1で作成したレイアウト生成関数を呼び出す分岐処理を追加します。

コールバック登録: app_main.pyで、2で作成したregister_new_page_callbacksをインポートし、呼び出します。

ナビゲーション追加: components/main_layout.pyのcreate_navbar関数に、新しいページへのリンクを追加します。

### 参考書マスターデータを更新する
text_data.csvを新しい参考書データで更新した後にupdate_master_textbooks.pyを実行します。

### 依存ライブラリを追加する
pip install <ライブラリ名>でライブラリをインストールします。

