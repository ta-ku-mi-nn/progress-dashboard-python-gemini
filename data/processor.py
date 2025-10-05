"""
データ処理関数
"""
import os
import pandas as pd
from config.settings import CSV_PATH, CSV_DTYPES, DEFAULT_STUDENT


def load_csv_data(user_filter=None):
    """CSVデータを読み込み、必要な列を追加
    
    Args:
        user_filter: ユーザーフィルター辞書 {'生徒': 'username'} または None（全データ）
    """
    # 達成割合を文字列として読み込み
    df = pd.read_csv(CSV_PATH, dtype=CSV_DTYPES)

    # 旧「ユーザー」列から「生徒」列への変換（下位互換性確保）
    if 'ユーザー' in df.columns and '生徒' not in df.columns:
        df = df.rename(columns={'ユーザー': '生徒'})
        # CSVファイルを更新して列名を変更
        df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
        print("CSVの「ユーザー」列を「生徒」列に変更しました")

    # 進捗用の列を追加（初期値False）
    if '予定' not in df.columns:
        df['予定'] = False
    if '達成済' not in df.columns:
        df['達成済'] = False
    if '達成割合' not in df.columns:
        df['達成割合'] = ''
    if '生徒' not in df.columns:
        df['生徒'] = DEFAULT_STUDENT  # デフォルト生徒を設定
        # CSVファイルを更新して生徒列を追加
        df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    if 'ユーザー名' not in df.columns:
        df['ユーザー名'] = ''  # デフォルトは空文字列
        # CSVファイルを更新してユーザー名列を追加
        df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    if '校舎' not in df.columns:
        df['校舎'] = ''  # デフォルトは空文字列
        # CSVファイルを更新して校舎列を追加
        df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    
    # ユーザーフィルターを適用
    if user_filter:
        for column, value in user_filter.items():
            if column in df.columns:
                df = df[df[column] == value]
    else:
        # 達成割合のNaN値を空文字列に変換
        df['達成割合'] = df['達成割合'].fillna('').astype(str)
        # 'nan'文字列も空文字列に変換
        df.loc[df['達成割合'] == 'nan', '達成割合'] = ''
        # 生徒列のNaN値をデフォルト生徒に変換
        df['生徒'] = df['生徒'].fillna(DEFAULT_STUDENT).astype(str)
        df.loc[df['生徒'] == 'nan', '生徒'] = DEFAULT_STUDENT

    return df


def save_csv_data(df):
    """DataFrameをCSVファイルに保存（バックアップ付き）"""
    import shutil
    import datetime
    
    try:
        # 保存前にバックアップを作成
        if os.path.exists(CSV_PATH):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"route-subject-text-time_backup_{timestamp}.csv"
            shutil.copy2(CSV_PATH, backup_path)
            print(f"📄 バックアップ作成: {backup_path}")
        
        # DataFrameの基本チェック
        if df.empty:
            print("⚠️ 警告: 空のDataFrameを保存しようとしています")
            return False
            
        print(f"💾 保存開始: {len(df)} 行のデータ")
        df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
        
        # 保存後の確認
        if os.path.exists(CSV_PATH):
            file_size = os.path.getsize(CSV_PATH)
            print(f"✅ 保存完了: ファイルサイズ {file_size} bytes")
            
        return True
    except (IOError, OSError, PermissionError) as e:
        print(f"❌ Error saving CSV data: {e}")
        return False


def add_new_book_data(df, route_level, subject, book_name, time_hours, current_user, user_campus=''):
    """新しい参考書データを追加"""
    new_data = {
        'ルートレベル': route_level,
        '科目': subject,
        '参考書名': book_name,
        '所要時間': time_hours,
        '予定': False,
        '達成済': False,
        '達成割合': '',
        '生徒': current_user,
        'ユーザー名': current_user,  # ユーザー名も記録
        '校舎': user_campus  # 校舎情報も記録
    }
    
    # 新しい行を追加
    new_df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    return new_df


def delete_book_data(df, book_indices):
    """指定されたインデックスの参考書データを削除"""
    return df.drop(book_indices).reset_index(drop=True)


def update_student_name(df, old_name, new_name):
    """生徒名を変更"""
    if '生徒' not in df.columns:
        # 生徒カラムが存在しない場合は追加
        df['生徒'] = DEFAULT_STUDENT
    df.loc[df['生徒'] == old_name, '生徒'] = new_name
    return df


def add_new_student_data(df, new_student_name, current_user_info=None):
    """新しい生徒のサンプルデータを追加（既存データを複製）"""
    # 生徒カラムが存在しない場合は追加
    if '生徒' not in df.columns:
        df['生徒'] = DEFAULT_STUDENT
        
    # デフォルト生徒のデータを取得（存在しない場合は最初の生徒のデータを使用）
    default_data = df[df['生徒'] == DEFAULT_STUDENT].copy()
    
    if default_data.empty and not df.empty:
        # デフォルト生徒が存在しない場合、最初の生徒のデータを取得
        first_student = df['生徒'].iloc[0] if '生徒' in df.columns else None
        if first_student:
            default_data = df[df['生徒'] == first_student].copy()
            print(f"🔄 デフォルト生徒が見つからないため、'{first_student}'のデータを複製します")
    
    if not default_data.empty:
        # 新しい生徒用にデータを複製
        new_student_data = default_data.copy()
        new_student_data['生徒'] = new_student_name
        # ユーザー名カラムを現在のユーザーに設定
        if 'ユーザー名' in new_student_data.columns and current_user_info:
            new_student_data['ユーザー名'] = current_user_info.get('username', '')
        # 校舎カラムを現在のユーザーの校舎に設定
        if '校舎' in new_student_data.columns and current_user_info:
            new_student_data['校舎'] = current_user_info.get('campus', '')
        # 進捗をリセット
        new_student_data['予定'] = False
        new_student_data['達成済'] = False
        new_student_data['達成割合'] = ''
        
        print(f"📊 新しい生徒データを追加: {len(new_student_data)} 行")
        
        # データを追加
        updated_df = pd.concat([df, new_student_data], ignore_index=True)
        return updated_df
    else:
        print("⚠️ 複製元のデータが見つかりません")
        return df


def get_user_accessible_data(user_info):
    """ユーザーがアクセス可能なデータを取得
    
    Args:
        user_info: ユーザー情報辞書（username, role, campus含む）
        
    Returns:
        フィルタリングされたDataFrame
    """
    df = load_csv_data()
    
    if user_info['role'] == 'admin':
        # 管理者は自分の校舎のデータ + デフォルト生徒データにアクセス可能
        user_campus = user_info.get('campus', '')
        if user_campus and '校舎' in df.columns:
            # 自分の校舎のデータ または デフォルト生徒データ（校舎が空/nan）
            campus_filter = (df['校舎'] == user_campus) | \
                          (df['校舎'].isna()) | \
                          (df['校舎'] == '') | \
                          (df['生徒'] == DEFAULT_STUDENT)
            return df[campus_filter]
        else:
            # 校舎情報がない場合は全データ（後方互換性）
            return df
    else:
        # 一般ユーザーは自分のデータ + デフォルト生徒データにアクセス可能
        if 'ユーザー名' in df.columns:
            # 自分が作成したデータ または デフォルト生徒データ（ユーザー名が空/nan）
            user_filter = (df['ユーザー名'] == user_info['username']) | \
                         (df['ユーザー名'].isna()) | \
                         (df['ユーザー名'] == '') | \
                         (df['ユーザー名'] == 'nan') | \
                         (df['生徒'] == DEFAULT_STUDENT)
            return df[user_filter]
        else:
            # ユーザー名カラムがない場合は生徒名で判断（後方互換性）
            return df[df['生徒'] == user_info['username']]


def initialize_user_data(username):
    """新規ユーザーのための初期データを作成
    
    Args:
        username: ユーザー名
    """
    df = load_csv_data()
    
    # ユーザーのデータが存在しない場合、サンプルデータを作成
    user_data = df[df['生徒'] == username]
    
    if user_data.empty:
        # サンプルデータを作成
        sample_entries = [
            {
                '科目': '数学',
                '参考書名': 'サンプル参考書（数学）',
                'ルートレベル': '基礎',
                '生徒': username,
                '予定': False,
                '達成済': False,
                '達成割合': '',
                '所要時間': 0.0
            },
            {
                '科目': '英語',
                '参考書名': 'サンプル参考書（英語）',
                'ルートレベル': '標準',
                '生徒': username,
                '予定': False,
                '達成済': False,
                '達成割合': '',
                '所要時間': 0.0
            }
        ]
        
        # DataFrameに追加
        new_df = pd.DataFrame(sample_entries)
        df = pd.concat([df, new_df], ignore_index=True)
        
        # CSVに保存
        save_csv_data(df)
        
        print(f"ユーザー '{username}' の初期データを作成しました")
        return df
    else:
        return df


def delete_student_data(df, student_name):
    """指定した生徒のデータを削除"""
    return df[df['生徒'] != student_name].reset_index(drop=True)


def calculate_achievement_stats(user_filter=None):
    """達成統計を計算
    
    Args:
        user_filter: ユーザーフィルター辞書
    """
    df = load_csv_data(user_filter)
    
    if df.empty:
        return {
            'total_books': 0,
            'planned_books': 0,
            'completed_books': 0,
            'completion_rate': 0
        }
    
    total_books = len(df)
    planned_books = len(df[df['予定'] == True])
    completed_books = len(df[df['達成済'] == True])
    
    completion_rate = (completed_books / total_books * 100) if total_books > 0 else 0
    
    return {
        'total_books': total_books,
        'planned_books': planned_books,
        'completed_books': completed_books,
        'completion_rate': completion_rate
    }

