# add_changelog_entry.py

import sqlite3
import os
from datetime import date

RENDER_DATA_DIR = "/var/data"
if os.path.exists(RENDER_DATA_DIR):
    DB_DIR = RENDER_DATA_DIR
else:
    DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_FILE = os.path.join(DB_DIR, 'progress.db')

def add_changelog_entries():
    """
    更新履歴のサンプルデータを追加します。
    """
    entries = [
        ('1.1.0', date(2025, 10, 12).isoformat(), '更新履歴機能の追加', 'サイドバーに「更新履歴」ページを追加し、アプリケーションの変更点を確認できるようにしました。'),
        ('1.0.0', date(2025, 10, 1).isoformat(), '初期リリース', '学習進捗ダッシュボードの最初のバージョンをリリースしました。主な機能: 進捗管理、宿題管理、過去問管理。')
    ]
    
    print("--- 更新履歴の追加を開始 ---")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.executemany(
            "INSERT INTO changelog (version, release_date, title, description) VALUES (?, ?, ?, ?)",
            entries
        )
        
        conn.commit()
        conn.close()
        print(f"  - {len(entries)} 件の更新履歴を追加しました。")
        print("--- 追加完了 ---")

    except sqlite3.Error as e:
        print(f"\n[エラー] データベース操作中にエラーが発生しました: {e}")

if __name__ == '__main__':
    add_changelog_entries()