# メンテナンス用ドキュメント

## 目次

- 概要  
- プロジェクト構成
- 主要ファイル解説
- メンテナンスガイド

## 概要
このドキュメントは、学習進捗ダッシュボードアプリケーションのメンテナンスと機能拡張を円滑に行うための手引書です。アプリケーションの全体像、各ファイルの役割、および一般的な修正手順について説明します。

## プロジェクト構成
本アプリケーションは、生徒の学習進捗を可視化し、管理するためのWebアプリケーションです。Dashフレームワークを基盤とし、データの永続化にはSQLiteを使用しています。


>/  
|-- auth/                 # 認証関連（ユーザー管理、セッション）  
|-- callbacks/            # Dashコールバック（アプリケーションの動的な振る舞いを定義）  
|-- charts/               # グラフ生成  
|-- components/           # レイアウトを構成するUI部品（モーダル、ナビゲーションバーなど）  
|-- config/               # アプリケーション設定（ポート番号、スタイル定義）  
|-- data/                 # データ処理（データベースとのやり取り）  
|-- utils/                # 補助的なユーティリティ（PDF生成など）  
|-- app_main.py           # アプリケーションのエントリーポイント  
|-- initialize_database.py # データベースの初期化スクリプト  
|-- progress.db           # アプリケーションデータベース  
|-- requirements.txt      # 依存ライブラリ一覧  
|-- text_data.csv         # 参考書マスターデータ  
|-- bulk_buttons.json     # 一括登録ボタンの初期設定  
|-- .gitignore            # Gitの追跡対象から除外するファイルを設定

## 主要ファイル解説
### app_main.py
アプリケーションの起動ファイルです。Dashインスタンスの生成、全体レイアウトの定義、Flaskサーバーのルーティング設定、そして各コールバックモジュールの登録を行います。

### initialize_database.py
progress.dbデータベースを初期状態に戻すためのスクリプトです。テーブルの全削除、再作成、そしてtext_data.csvやbulk_buttons.jsonからの初期データ投入を行います。

### data/nested_json_processor.py
データベースとの接続(CRUD操作)を担う重要なモジュールです。生徒情報、進捗、宿題、マスターデータなど、アプリケーションで利用するほぼ全てのデータ操作関数がここに集約されています。

### callbacks/ ディレクトリ
各ページの動的な振る舞いを定義するコールバック関数が機能ごとにまとめられています。

main_callbacks.py: 全体レイアウト、生徒選択時の処理。

auth_callbacks.py: ログイン・ログアウト、プロファイル表示。

progress_callbacks.py: ダッシュボードのグラフやテーブル表示。

その他、各機能（管理者、宿題、計画など）に対応したファイル。

### components/ ディレクトリ
アプリケーションのUIを構成する再利用可能なレイアウト部品が格納されています。モーダルウィンドウやナビゲーションバー、各ページの基本レイアウトなどが定義されています。

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

