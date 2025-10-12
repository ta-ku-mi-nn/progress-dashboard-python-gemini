# restore_database.py

import os
import shutil
import sys
from datetime import datetime

# --- 設定 ---
# Render環境でのデータベースパスを指定
RENDER_DATA_DIR = "/var/data"
DATABASE_FILE = os.path.join(RENDER_DATA_DIR, 'progress.db')

def restore_database(backup_file_path):
    """
    指定されたバックアップファイルで本番のデータベースを上書き復元する。
    """
    # 1. 復元元ファイルの存在確認
    if not os.path.exists(backup_file_path):
        print(f"エラー: 指定されたバックアップファイルが見つかりません。")
        print(f"パスを確認してください: {backup_file_path}")
        return

    # 2. 最終確認
    print("="*60)
    print("警告: これからデータベースの復元を実行します。")
    print(f"復元元ファイル: {backup_file_path}")
    print(f"復元先ファイル: {DATABASE_FILE}")
    print("\n現在のデータベースは上書きされ、データは失われます。")
    print("="*60)
    
    response = input("本当に実行してもよろしいですか？ (yes/no): ").lower()
    if response != 'yes':
        print("\n処理を中断しました。")
        return

    try:
        # 3. 念のため現在のDBをバックアップ
        current_db_backup_path = f"{DATABASE_FILE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
        if os.path.exists(DATABASE_FILE):
            shutil.copy(DATABASE_FILE, current_db_backup_path)
            print(f"\n現在のデータベースをバックアップしました: {current_db_backup_path}")

        # 4. バックアップファイルで上書き
        shutil.copy(backup_file_path, DATABASE_FILE)
        print(f"データベースを正常に復元しました。")
        print("アプリケーションを再起動して変更を適用してください。")

    except Exception as e:
        print(f"\n[エラー] 復元中にエラーが発生しました: {e}")

if __name__ == '__main__':
    # コマンドライン引数からバックアップファイルのパスを取得
    if len(sys.argv) < 2:
        print("エラー: 復元するバックアップファイルのパスを引数として指定してください。")
        print("使用法: python restore_database.py <バックアップファイルのパス>")
    else:
        backup_path = sys.argv[1]
        restore_database(backup_path)