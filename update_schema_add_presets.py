# add_new_preset.py

import sqlite3
import os

# --- データベースファイルのパス設定 ---
# RenderのDiskマウントパス（/var/data）が存在すればそちらを使用
RENDER_DATA_DIR = "/var/data"
if os.path.exists(RENDER_DATA_DIR):
    # 本番環境（Render）用のパス
    DB_DIR = RENDER_DATA_DIR
else:
    # ローカル開発環境用のパス
    DB_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_FILE = os.path.join(DB_DIR, 'progress.db')


def add_preset_to_db(subject, preset_name, book_names):
    """
    指定されたプリセット情報をデータベースに追加します。
    """
    if not isinstance(book_names, list) or not book_names:
        print("[エラー] 参考書リストが空です。")
        return

    print(f"--- プリセットの追加を開始: [{subject}] {preset_name} ---")
    
    conn = None  # finallyブロックで使えるように外で定義
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # 1. bulk_presetsテーブルにプリセット名を追加
        try:
            cursor.execute(
                "INSERT INTO bulk_presets (subject, preset_name) VALUES (?, ?)",
                (subject, preset_name)
            )
        except sqlite3.IntegrityError:
            print(f"-> プリセット '{preset_name}' は既に存在するため、スキップします。")
            return

        # 2. 追加したプリセットのIDを取得
        preset_id = cursor.lastrowid
        print(f"  - プリセット '{preset_name}' をID: {preset_id} で作成しました。")

        # 3. bulk_preset_booksテーブルに関連する参考書を追加
        book_inserts = [(preset_id, book_name) for book_name in book_names]
        cursor.executemany(
            "INSERT INTO bulk_preset_books (preset_id, book_name) VALUES (?, ?)",
            book_inserts
        )
        print(f"  - {len(book_inserts)}冊の参考書をプリセットに関連付けました。")

        conn.commit()
        print("\n🎉 プリセットの追加が正常に完了しました！")

    except sqlite3.Error as e:
        print(f"\n[エラー] データベース操作中にエラーが発生しました: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            print("--- 処理完了 ---")


if __name__ == '__main__':
    # ### ▼▼▼ 新しいプリセット情報をここに設定 ▼▼▼ ###

    # 例1: 英語の日大レベル基本セット
    NEW_SUBJECT = "英語"
    NEW_PRESET_NAME = "日大レベル入門セット"
    NEW_BOOK_NAMES = [
        "システム英単語basic",
        "大岩のいちばんはじめの英文法超基礎文法編",
        "高校基礎英文法パターンドリル",
        "高校英文読解をひとつひとつわかりやすく。"
    ]
    
    # データベースに追加処理を実行
    add_preset_to_db(NEW_SUBJECT, NEW_PRESET_NAME, NEW_BOOK_NAMES)

    # --- 他のプリセットを追加したい場合は、以下のように追記できます ---
    # 例2: 数学の日大レベル基本セット
    # add_preset_to_db(
    #     "数学",
    #     "日大レベル 数学I・Aセット",
    #     [
    #         "数学Ⅰ・A 入門問題精講",
    #         "数学Ⅰ・A 基礎問題精講",
    #         "ドラゴン桜式 数学力ドリル 数学1・A"
    #     ]
    # )
    
    # ### ▲▲▲ 設定はここまで ▲▲▲ ###