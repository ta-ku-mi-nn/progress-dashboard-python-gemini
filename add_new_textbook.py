import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from data.nested_json_processor import add_master_textbook

def main():
    print("=== 新規参考書追加ツール ===")
    print("データベースに新しい参考書情報を追加します。")
    print("中断するには Ctrl+C を押してください。\n")

    while True:
        try:
            print("-" * 30)
            subject = input("科目 (例: 英語): ").strip()
            if not subject:
                print("科目は必須です。")
                continue

            level = input("レベル (例: 日大, MARCH): ").strip()
            if not level:
                print("レベルは必須です。")
                continue

            book_name = input("参考書名: ").strip()
            if not book_name:
                print("参考書名は必須です。")
                continue

            duration_str = input("標準所要時間 (時間, 例: 10.5): ").strip()
            try:
                duration = float(duration_str)
            except ValueError:
                print("所要時間は数値で入力してください。")
                continue

            print(f"\n以下の内容で登録しますか？")
            print(f"  科目: {subject}")
            print(f"  レベル: {level}")
            print(f"  参考書名: {book_name}")
            print(f"  所要時間: {duration} 時間")

            confirm = input("登録しますか？ (y/n): ").strip().lower()
            if confirm == 'y':
                success, message = add_master_textbook(subject, level, book_name, duration)
                if success:
                    print(f"\n✅ 成功: {message}")
                else:
                    print(f"\n❌ 失敗: {message}")
            else:
                print("\nキャンセルしました。")

            retry = input("\n続けて追加しますか？ (y/n): ").strip().lower()
            if retry != 'y':
                break

        except KeyboardInterrupt:
            print("\n\n終了します。")
            break
        except Exception as e:
            print(f"\n予期せぬエラーが発生しました: {e}")
            break

if __name__ == "__main__":
    main()
