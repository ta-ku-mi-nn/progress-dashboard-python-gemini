# update_database_schema.py

import sqlite3
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

def add_column_if_not_exists(cursor, table_name, column_name, column_type):
    """テーブルに指定されたカラムが存在しない場合のみ追加する"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        print(f"  - '{table_name}' テーブルに '{column_name}' カラムを追加しました。")
    else:
        print(f"  - '{column_name}' カラムは既に存在するため、スキップします。")

def update_schema():
    """
    データベーススキーマを更新するスクリプト。
    - progressテーブルに completed_units, total_units を追加し、既存データを移行
    - studentsテーブルに deviation_value を追加
    """
    if not os.path.exists(DATABASE_FILE):
        print(f"エラー: データベースファイル '{DATABASE_FILE}' が見つかりません。")
        return

    print("="*50)
    print("データベーススキーマの更新を開始します...")
    print("="*50)

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # 1. progress テーブルにカラムを追加
        print("1. 'progress' テーブルを更新中...")
        add_column_if_not_exists(cursor, 'progress', 'completed_units', 'INTEGER NOT NULL DEFAULT 0')
        add_column_if_not_exists(cursor, 'progress', 'total_units', 'INTEGER NOT NULL DEFAULT 1')

        # 既存データの移行: is_done=True のレコードを completed=1, total=1 に設定
        cursor.execute("UPDATE progress SET completed_units = 1, total_units = 1 WHERE is_done = 1;")
        cursor.execute("UPDATE progress SET completed_units = 0, total_units = 1 WHERE is_done = 0;")
        print("  - 既存の 'is_done' データを新しい達成割合カラムに移行しました。")

        # 2. students テーブルにカラムを追加
        print("\n2. 'students' テーブルを更新中...")
        add_column_if_not_exists(cursor, 'students', 'deviation_value', 'INTEGER')
        
        # サンプルとして、生徒に偏差値を設定
        cursor.execute("UPDATE students SET deviation_value = 65 WHERE name = '生徒1' AND school = '東京校'")
        cursor.execute("UPDATE students SET deviation_value = 55 WHERE name = '生徒2' AND school = '東京校'")
        print("  - テスト用に '東京校' の生徒に偏差値65と55を設定しました。")

        conn.commit()
        conn.close()

        print("\n" + "="*50)
        print("🎉 スキーマの更新が正常に完了しました！")
        print("   'progress' テーブルに達成割合用のカラムが追加されました。")
        print("   'students' テーブルに偏差値用のカラムが追加されました。")
        print("="*50)

    except sqlite3.Error as e:
        print(f"\n[エラー] データベース操作中にエラーが発生しました: {e}")

if __name__ == '__main__':
    update_schema()