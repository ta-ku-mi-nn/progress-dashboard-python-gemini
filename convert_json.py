import json
import datetime

# --- 設定 ---
OLD_FILE_NAME = 'route-subject-text-time.json'
NEW_FILE_NAME = 'route-subject-text-time_new.json' # 上書きを防ぐため新しいファイル名で保存

def convert_data_structure():
    """
    古いデータ構造のJSONファイルを読み込み、新しい構造に変換して保存します。
    古い構造: 校舎 -> ユーザー -> 生徒 -> progress
    新しい構造: 校舎 -> 生徒 -> {data, progress}
    """
    print(f"'{OLD_FILE_NAME}' を読み込んでいます...")
    try:
        with open(OLD_FILE_NAME, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
    except FileNotFoundError:
        print(f"エラー: '{OLD_FILE_NAME}' が見つかりません。ファイルが正しい場所にあるか確認してください。")
        return
    except json.JSONDecodeError:
        print(f"エラー: '{OLD_FILE_NAME}' のJSON形式が正しくありません。")
        return

    # 新しいデータ構造を格納する辞書を初期化
    new_data_content = {}
    
    print("データ構造を変換中...")
    # 古いデータ構造をループして、新しい構造に組み替える
    for school, users in old_data.get('data', {}).items():
        if school not in new_data_content:
            new_data_content[school] = {}
            
        for user, students in users.items():
            for student_name, student_details in students.items():
                
                # 生徒データが既に存在する場合（ありえないはずだが念のため）はスキップ
                if student_name in new_data_content[school]:
                    print(f"警告: 生徒 '{student_name}' が校舎 '{school}' に既に存在します。スキップします。")
                    continue
                
                # 新しい生徒オブジェクトを作成
                new_student_object = {
                    "data": {
                        "偏差値": student_details.get("student_data", {}).get("偏差値", 50), # 既存のstudent_dataから取得、なければ50
                        "メイン講師": user,
                        "サブ講師": "" # サブ講師は空で初期化
                    },
                    "progress": student_details.get("progress", {})
                }
                
                # 新しいデータ構造に生徒を追加
                new_data_content[school][student_name] = new_student_object

    # 新しいJSONファイル全体（メタデータ＋データ）の構造を作成
    new_full_json = {
        "metadata": {
            "created": old_data.get("metadata", {}).get("created", datetime.datetime.now().isoformat()),
            "last_updated": datetime.datetime.now().isoformat(),
            "version": "4.0",
            "structure": "nested",
            "source": old_data.get("metadata", {}).get("source", "N/A"),
            "description": "校舎→生徒→{data, progress}の階層構造"
        },
        "data": new_data_content
    }

    print(f"変換後のデータを '{NEW_FILE_NAME}' に保存しています...")
    try:
        with open(NEW_FILE_NAME, 'w', encoding='utf-8') as f:
            json.dump(new_full_json, f, indent=2, ensure_ascii=False)
        print("✅ 変換が正常に完了しました。")
        print(f"次に `config/settings.py` の 'json_file' を '{NEW_FILE_NAME}' に変更してください。")
    except Exception as e:
        print(f"エラー: ファイルの保存に失敗しました: {e}")

if __name__ == '__main__':
    convert_data_structure()