# bulk_school_updater.py
import os
import psycopg2
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
# このスクリプトを実行する場所に .env ファイルが存在し、
# DATABASE_URL が設定されている必要があります。
load_dotenv()

# --- 設定 ---
# 環境変数からデータベースURLを取得
DATABASE_URL = os.getenv('DATABASE_URL')
OLD_SCHOOL_NAME = '東京校'
NEW_SCHOOL_NAME = '鷺沼校'

def get_db_connection():
    """PostgreSQLデータベース接続を取得します。"""
    if not DATABASE_URL:
        raise ValueError("エラー: 環境変数 'DATABASE_URL' が設定されていません。")
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def bulk_update_student_school(old_school_name, new_school_name):
    """
    指定された校舎名に所属するすべての生徒の校舎情報を一括で更新します。

    Args:
        old_school_name (str): 変更元の校舎名
        new_school_name (str): 変更先の校舎名

    Returns:
        tuple: (bool: 成功/失敗, str: メッセージ)
    """
    conn = None # connをNoneで初期化
    updated_count = 0
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # UPDATEクエリを実行
            cur.execute(
                "UPDATE students SET school = %s WHERE school = %s",
                (new_school_name, old_school_name)
            )
            # 更新された行数を取得
            updated_count = cur.rowcount

        conn.commit()
        if updated_count > 0:
            return True, f"{updated_count}人の生徒の校舎を「{old_school_name}」から「{new_school_name}」に変更しました。"
        else:
            return True, f"「{old_school_name}」に所属する生徒が見つからなかったため、変更はありませんでした。"
    except (Exception, psycopg2.Error) as e: # Exceptionを追加
        print(f"校舎情報の一括更新エラー: {e}")
        if conn:
            conn.rollback()
        return False, f"校舎情報の更新中にエラーが発生しました: {e}"
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("="*60)
    print("生徒の校舎情報一括変更スクリプト")
    print(f"変更元校舎: {OLD_SCHOOL_NAME}")
    print(f"変更先校舎: {NEW_SCHOOL_NAME}")
    print(f"対象データベース: {DATABASE_URL.split('@')[-1] if DATABASE_URL else '未設定'}")
    print("\n警告: この操作は元に戻せません。実行前にデータベースのバックアップを推奨します。")
    print("="*60)

    response = input("実行しますか？ (yes/no): ").lower()

    if response == 'yes':
        print("\n処理を開始します...")
        success, message = bulk_update_student_school(OLD_SCHOOL_NAME, NEW_SCHOOL_NAME)
        print(message)
        if success:
            print("✅ 処理が完了しました。")
        else:
            print("❌ 処理中にエラーが発生しました。")
    else:
        print("\n処理を中断しました。")