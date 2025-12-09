import sys
import os
import pandas as pd

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from data.nested_json_processor import add_master_textbook
from config.settings import APP_CONFIG

def main():
    print("=== CSVファイルからの参考書一括追加ツール ===")
    
    # --- 接続先確認 ---
    db_url = APP_CONFIG['data']['database_url']
    # セキュリティのためパスワード等は隠してホスト名などを表示するのが理想ですが、
    # ここでは簡易的にURLの一部で判定して表示します。
    if "render.com" in db_url:
        print("🌍 接続先: Render (本番環境のデータベース)")
    elif "localhost" in db_url or "127.0.0.1" in db_url:
        print("🏠 接続先: Localhost (ローカルデータベース)")
    else:
        print(f"🔗 接続先: {db_url}")
    
    print("指定されたCSVファイルを読み込み、データベースに追加します。")
    print("既存のデータは削除されず、重複するデータはスキップされます。\n")

    default_csv = 'new_textbooks_sample.csv'
    csv_file = input(f"読み込むCSVファイル名を入力してください (デフォルト: {default_csv}): ").strip()
    if not csv_file:
        csv_file = default_csv

    if not os.path.exists(csv_file):
        print(f"\n❌ エラー: ファイル '{csv_file}' が見つかりません。")
        return

    try:
        # CSV読み込み
        # update_master_textbooks.py に合わせてカラム名を指定
        # 想定ヘッダー: level, subject, book_name, duration
        df = pd.read_csv(csv_file, encoding='utf-8')
        
        # カラム名の正規化（空白除去など）
        df.columns = [c.strip() for c in df.columns]
        
        required_columns = {'ルートレベル', '科目', '参考書名', '所要時間'}
        if not required_columns.issubset(df.columns):
            print(f"\n❌ エラー: CSVファイルに必要なカラムが含まれていません。")
            print(f"必要なカラム: {required_columns}")
            print(f"検出されたカラム: {df.columns.tolist()}")
            return

        print(f"\n'{csv_file}' から {len(df)} 件のデータを読み込みました。登録を開始します...\n")

        success_count = 0
        skip_count = 0
        error_count = 0

        for index, row in df.iterrows():
            subject = row['科目']
            level = row['ルートレベル']
            book_name = row['参考書名']
            duration = row['所要時間']

            # データのバリデーション
            if pd.isna(subject) or pd.isna(level) or pd.isna(book_name):
                print(f"⚠️ 行 {index+2}: 必須項目が欠けているためスキップします。")
                error_count += 1
                continue

            try:
                duration = float(duration) if not pd.isna(duration) else 0.0
            except ValueError:
                print(f"⚠️ 行 {index+2}: 所要時間が数値ではないため 0.0 として扱います。")
                duration = 0.0

            # 登録処理
            success, message = add_master_textbook(subject, level, book_name, duration)
            
            if success:
                print(f"✅ 追加: {subject} - {book_name}")
                success_count += 1
            else:
                # 重複などの場合
                if "既に存在します" in message:
                    print(f"⏭️ スキップ (重複): {subject} - {book_name}")
                    skip_count += 1
                else:
                    print(f"❌ エラー: {subject} - {book_name} -> {message}")
                    error_count += 1

        print("\n" + "="*30)
        print("処理完了")
        print(f"  成功: {success_count} 件")
        print(f"  スキップ: {skip_count} 件")
        print(f"  エラー: {error_count} 件")
        print("="*30)

    except Exception as e:
        print(f"\n❌ 予期せぬエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
