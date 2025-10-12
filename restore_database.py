# restore_from_deploy.py

import os
import shutil
from datetime import datetime

# --- 設定 ---
# Renderの永続ディスクのパス
RENDER_DATA_DIR = "/var/data"
# 復元先のデータベースファイルパス
DEST_DB_PATH = os.path.join(RENDER_DATA_DIR, 'dashboard_backup_20251012_134318.db')

# デプロイされた（復元元となる）データベースファイルのパス
# このスクリプトと同じ階層にあることを想定
SOURCE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard_backup_20251012_134318.db')

def restore_database():
    """
    デプロイされた dashboard_backup_20251012_134318.db を永続ディスクにコピーしてデータベースを復元する。
    """
    # 1. 復元元ファイルの存在確認
    if not os.path.exists(SOURCE_DB_PATH):
        print(f"エラー: デプロイされた 'dashboard_backup_20251012_134318.db' が見つかりません。")
        print("プロジェクトのルートに 'dashboard_backup_20251012_134318.db' を含めてデプロイしてください。")
        return

    # 2. 最終確認
    print("="*60)
    print("これからデプロイされたDBファイルを使って、データベースを復元します。")
    print(f"\n復元元: {SOURCE_DB_PATH} (デプロイされたファイル)")
    print(f"復元先: {DEST_DB_PATH} (永続ディスク上の本番DB)")
    print("\n現在の本番データは上書きされます！")
    print("="*60)
    
    response = input("本当に実行してもよろしいですか？ (yes/no): ").lower()
    if response != 'yes':
        print("\n処理を中断しました。")
        return

    try:
        # 3. 念のため現在のDBをバックアップ
        if os.path.exists(DEST_DB_PATH):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{DEST_DB_PATH}_{timestamp}.bak"
            shutil.copy(DEST_DB_PATH, backup_path)
            print(f"\n現在のデータベースをバックアップしました: {backup_path}")

        # 4. デプロイされたファイルで上書きコピー
        shutil.copy(SOURCE_DB_PATH, DEST_DB_PATH)
        print(f"\n✅ データベースを正常に復元しました。")
        print("   Renderの管理画面からサービスを再起動してください。")

    except Exception as e:
        print(f"\n[エラー] 復元中にエラーが発生しました: {e}")

if __name__ == '__main__':
    restore_database()