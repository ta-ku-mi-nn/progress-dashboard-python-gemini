import json
import os
import threading
from config.settings import APP_CONFIG

# --- 設定ファイルからファイルパスを取得 ---
DATA_FILE_PATH = APP_CONFIG['data']['json_file']
# --- ファイルへの同時アクセスによるデータ破損を防ぐためのロック ---
LOCK = threading.Lock()

def load_json_data():
    """
    アプリケーションのメインデータとなるJSONファイルを読み込み、'data'キーの内容を返す。
    アプリケーション起動時に一度だけ呼び出されることを想定しています。
    """
    with LOCK:
        try:
            with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 'data'キーに格納されている実際の進捗データを返す
            return data.get('data', {})
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"エラー: データファイルの読み込みに失敗しました。ファイルパス: {DATA_FILE_PATH}, エラー: {e}")
            return {} # エラーが発生した場合は空の辞書を返す

def save_json_data(full_data_content):
    """
    全体のJSONデータ（メタデータと進捗データを含む）をファイルに保存する。
    
    Args:
        full_data_content (dict): 'metadata'キーと'data'キーを含む完全な辞書オブジェクト。
    """
    with LOCK:
        try:
            with open(DATA_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(full_data_content, f, indent=2, ensure_ascii=False)
            return True, "データの保存に成功しました。"
        except Exception as e:
            return False, f"データの保存中にエラーが発生しました: {e}"

def initialize_user_data(username):
    """
    新規ユーザー向けのデータ構造を初期化する（必要に応じて）。
    現在は特別な処理を行わないプレースホルダーです。
    """
    pass

# --- データ取得用ヘルパー関数群（新データ構造対応） ---

def get_all_schools(data):
    """データオブジェクトからすべての校舎名のリストを取得する"""
    return list(data.keys()) if data else []

def get_students_for_user(data, school, user_info):
    """
    指定された校舎とユーザー情報に基づき、アクセス可能な生徒のリストを取得する。
    管理者はその校舎の全生徒、一般ユーザーは自分が担当する生徒のみ。
    """
    if not data or not school or not user_info:
        return []

    school_data = data.get(school, {})
    
    # 管理者の場合は校舎の全生徒を返す
    if user_info.get('role') == 'admin':
        return list(school_data.keys())
    
    # 一般ユーザーの場合は、自分がメイン講師またはサブ講師である生徒を返す
    username = user_info.get('username')
    accessible_students = []
    for student_name, student_details in school_data.items():
        student_specific_data = student_details.get('data', {})
        if student_specific_data.get('メイン講師') == username or student_specific_data.get('サブ講師') == username:
            accessible_students.append(student_name)
            
    return accessible_students

def get_all_subjects(data):
    """データセット全体から重複しない科目のリストを取得する"""
    subjects = set()
    if not data:
        return []
    for school_data in data.values():
        for student_data in school_data.values():
            if 'progress' in student_data and isinstance(student_data['progress'], dict):
                subjects.update(student_data['progress'].keys())
    return sorted(list(subjects))

def get_student_progress(data, school, student):
    """特定の生徒の進捗データ（全科目）を取得する"""
    try:
        return data[school][student].get('progress', {})
    except KeyError:
        # 生徒データが存在しない場合は空の辞書を返す
        return {}

def get_student_info(data, school, student):
    """特定の生徒の個人情報（偏差値、講師など）を取得する"""
    try:
        return data[school][student].get('data', {})
    except KeyError:
        return {}