import json
from werkzeug.security import generate_password_hash
from config.settings import APP_CONFIG

# --- ここに登録したいユーザー情報を追加・編集してください ---
USERS_TO_CREATE = [
    {
        "username": "admin",
        "password": "admin", # 平文のパスワード
        "role": "admin",
        "school": "デフォルト校舎"
    },
    {
        "username": "tokyo_user1",
        "password": "user",
        "role": "user",
        "school": "東京校"
    },
    {
        "username": "osaka_admin",
        "password": "admin",
        "role": "admin",
        "school": "大阪校"
    },
    # 必要に応じて他のユーザーを追加
]

def create_users_file():
    """
    USERS_TO_CREATEリストに基づいて、パスワードをハッシュ化したusers.jsonを生成します。
    """
    users_data = {}
    for user_info in USERS_TO_CREATE:
        username = user_info["username"]
        users_data[username] = {
            "username": username,
            "password": generate_password_hash(user_info["password"]), # パスワードをハッシュ化
            "role": user_info["role"],
            "school": user_info["school"]
        }
        print(f"ユーザー '{username}' を作成しました。")

    # 設定ファイルから保存先のファイル名を取得
    users_file_path = APP_CONFIG['data']['users_file']

    try:
        with open(users_file_path, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ '{users_file_path}' が正常に作成されました。")
    except Exception as e:
        print(f"\n❌ エラー: ファイルの保存に失敗しました: {e}")

if __name__ == '__main__':
    create_users_file()