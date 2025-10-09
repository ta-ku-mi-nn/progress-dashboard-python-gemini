# setup_bulk_presets.py

import sqlite3
import json
import os

# RenderのDiskマウントパス（/var/data）が存在すればそちらを使用
RENDER_DATA_DIR = "/var/data"
if os.path.exists(RENDER_DATA_DIR):
    # 本番環境（Render）用のパス
    DB_DIR = RENDER_DATA_DIR
else:
    # ローカル開発環境用のパス (プロジェクトのルートディレクトリを指す)
    # このファイルの2階層上がプロジェクトルート
    DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_FILE = os.path.join(DB_DIR, 'progress.db')
JSON_FILE = 'bulk_buttons.json'

def setup_bulk_presets():
    """
    bulk_buttons.jsonの内容をデータベースの新しいテーブルに移行する。
    """
    if not os.path.exists(DATABASE_FILE):
        print(f"エラー: データベースファイル '{DATABASE_FILE}' が見つかりません。")
        return
        
    if not os.path.exists(JSON_FILE):
        print(f"エラー: '{JSON_FILE}' が見つかりません。移行元のデータがありません。")
        return

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    print("--- 一括登録ボタンのデータベース移行を開始 ---")

    # 1. テーブルの作成
    # bulk_presets: ボタンのグループを定義するテーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bulk_presets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            preset_name TEXT NOT NULL,
            UNIQUE(subject, preset_name)
        )
    ''')
    # bulk_preset_books: 各グループにどの参考書が含まれるかを定義するテーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bulk_preset_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preset_id INTEGER NOT NULL,
            book_name TEXT NOT NULL,
            FOREIGN KEY (preset_id) REFERENCES bulk_presets (id)
        )
    ''')
    print("  - テーブル 'bulk_presets' と 'bulk_preset_books' を準備しました。")

    # 2. 既存のデータをクリア
    cursor.execute("DELETE FROM bulk_preset_books;")
    cursor.execute("DELETE FROM bulk_presets;")
    print("  - 既存のデータをクリアしました。")

    # 3. JSONファイルからデータを読み込み、DBに挿入
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    for subject, presets in config.items():
        for preset_name, books in presets.items():
            # presetを登録
            cursor.execute(
                "INSERT INTO bulk_presets (subject, preset_name) VALUES (?, ?)",
                (subject, preset_name)
            )
            preset_id = cursor.lastrowid # 登録したpresetのIDを取得

            # 関連する参考書を登録
            book_inserts = [(preset_id, book_name) for book_name in books]
            cursor.executemany(
                "INSERT INTO bulk_preset_books (preset_id, book_name) VALUES (?, ?)",
                book_inserts
            )
    
    conn.commit()
    conn.close()

    print(f"  - '{JSON_FILE}' からのデータ移行が完了しました。")
    print("--- 移行完了 ---")

if __name__ == '__main__':
    setup_bulk_presets()