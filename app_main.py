# app_main.py

#!/usr/bin/env python3
"""
学習進捗ダッシュボード - PostgreSQL版 認証機能付きメインアプリケーション
"""
import sys
import os
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, no_update # ★ no_update をインポート
import plotly.io as pio
from flask import request, jsonify # Flaskのrequestとjsonifyを追加
import json # jsonを追加
from data.nested_json_processor import get_db_connection
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime, date # date をインポート

# --- グラフ描画の安定化のため、デフォルトテンプレートを設定 ---
pio.templates.default = "plotly_white"

# --- プロジェクトのルートディレクトリをPythonのパスに追加 ---
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


# --- 設定と外部ファイルのインポート ---
from config.settings import APP_CONFIG
from config.styles import APP_INDEX_STRING, EXTERNAL_STYLESHEETS
from data.nested_json_processor import (
    get_all_subjects, get_student_info_by_id,
    get_student_count_by_school, get_textbook_count_by_subject,
    add_past_exam_result, add_acceptance_result,
    add_mock_exam_result # ★★★ add_mock_exam_result をインポート ★★★
)
from components.main_layout import create_main_layout, create_navbar
from components.homework_layout import create_homework_layout
from components.modals import create_all_modals
from components.admin_components import (
    create_master_textbook_modal, create_textbook_edit_modal,
    create_student_edit_modal, create_student_management_modal,
    create_bulk_preset_management_modal, create_bulk_preset_edit_modal,
    create_user_edit_modal,
    create_add_changelog_modal,
    create_mock_exam_list_modal
)
from components.modals import create_user_list_modal, create_new_user_modal
from components.login_components import (
    create_login_layout,
    create_access_denied_layout,
    create_user_profile_modal, create_password_change_modal
)
from components.bug_report_layout import create_bug_report_layout
from components.past_exam_layout import create_past_exam_layout
from components.howto_layout import create_howto_layout
from components.changelog_layout import create_changelog_layout
from components.report_layout import create_report_layout
from callbacks.main_callbacks import register_main_callbacks
from callbacks.progress_callbacks import register_progress_callbacks
from callbacks.admin_callbacks import register_admin_callbacks
from callbacks.auth_callbacks import register_auth_callbacks
from callbacks.homework_callbacks import register_homework_callbacks
from callbacks.report_callbacks import register_report_callbacks
from callbacks.plan_callbacks import register_plan_callbacks
from callbacks.bug_report_callbacks import register_bug_report_callbacks
from callbacks.past_exam_callbacks import register_past_exam_callbacks
from components.statistics_layout import create_statistics_layout
from callbacks.statistics_callbacks import register_statistics_callbacks
from components.root_table_layout import create_root_table_layout
from callbacks.root_table_callbacks import register_root_table_callbacks


# ★★★ APIキーを設定 (実際の運用では環境変数などを使用) ★★★
API_KEY = os.getenv("FORM_API_KEY", "YOUR_SECRET_API_KEY") # 環境変数から取得、なければデフォルト値

# --- アプリケーションの初期化 ---
app = dash.Dash(
    __name__,
    external_stylesheets=EXTERNAL_STYLESHEETS,
    suppress_callback_exceptions=True,
    title="学習進捗ダッシュボード"
)
app.index_string = APP_INDEX_STRING
# Flaskサーバーのシークレットキーを設定
# 環境変数から取得するか、なければデフォルト値を設定
app.server.secret_key = os.getenv('SECRET_KEY', APP_CONFIG['server']['secret_key'])
server = app.server # Flaskサーバーインスタンスを取得

# --- メインレイアウト ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=True), # ★ refresh=True はそのまま
    dcc.Store(id='auth-store', storage_type='session'),
    dcc.Store(id='school-selection-store', storage_type='session'),
    dcc.Store(id='student-selection-store', storage_type='session'),
    dcc.Store(id='admin-update-trigger', storage_type='memory'),
    dcc.Store(id='toast-trigger', storage_type='memory'),
    dcc.Store(id='item-to-delete-store', storage_type='memory'), # 汎用削除IDストア
    dcc.Store(id='save-status-result-store', storage_type='memory'),

    html.Div(id='dummy-clientside-output', style={'display': 'none'}), # clientside callback 用
    dcc.Store(id='report-content-store', storage_type='session'), # レポート印刷用
    html.Div(id='navbar-container'), # ナビゲーションバー

    dbc.Container([
        html.Div(id='school-dropdown-container'), # （削除またはコメントアウト予定）
        html.Div(id='student-dropdown-container', className="mb-3"), # 生徒選択ドロップダウン
        html.Div(id='page-content'), # 各ページのコンテンツ
    ], fluid=True, className="mt-4"),

    # 共通コンポーネント
    dbc.Toast( # 成功通知
        id="success-toast", header="成功", is_open=False, dismissable=True,
        icon="success", duration=4000,
        style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 9999},
    ),
    create_user_profile_modal(), # ユーザープロファイルモーダル
    create_password_change_modal(), # パスワード変更モーダル
    dcc.Download(id="download-pdf-report"), # PDFダウンロード用
    dcc.Download(id="download-backup") # バックアップダウンロード用
])

# --- ヘルパー関数 ---
def get_current_user_from_store(auth_store_data):
    """dcc.Storeのデータから現在のユーザー情報を取得"""
    return auth_store_data if auth_store_data and isinstance(auth_store_data, dict) else None

# --- ページ表示コールバック（ルーティング） (★修正箇所) ---
@app.callback(
    [Output('page-content', 'children'),
     Output('navbar-container', 'children'),
     Output('url', 'pathname', allow_duplicate=True)], # ★ Output に 'url.pathname' を追加
    [Input('url', 'pathname'),
     Input('auth-store', 'data')],
    prevent_initial_call=True # ★ allow_duplicate=True と prevent_initial_call=True を設定
)
def display_page(pathname, auth_store_data):
    """URLのパスに応じてページコンテンツとナビゲーションバーを切り替え"""
    user_info = get_current_user_from_store(auth_store_data)

    # ログインしていない場合
    if not user_info:
        # ログインページを表示し、ナビゲーションバーは非表示、URLを/loginに
        # return create_login_layout(), None # <-- ★ 変更
        return create_login_layout(), None, '/login' # ★ URLも返す

    # レポート印刷ページの場合
    if pathname and pathname.startswith('/report/'):
        try:
            student_id = int(pathname.split('/')[-1])
            student_info = get_student_info_by_id(student_id)
            if not student_info: # 生徒情報が見つからない場合
                 # return dbc.Alert("指定された生徒が見つかりません。", color="danger"), create_navbar(user_info) # <-- ★ 変更
                 return dbc.Alert("指定された生徒が見つかりません。", color="danger"), create_navbar(user_info), no_update # ★ URLは更新しない
            student_name = student_info.get('name', '不明な生徒')
            # レポートページではナビゲーションバーを非表示
            # return create_report_layout(student_name), None # <-- ★ 変更
            return create_report_layout(student_name), None, no_update # ★ URLは更新しない
        except (ValueError, IndexError):
            # 不正なURLの場合
            # return dbc.Alert("無効なURLです。", color="danger"), create_navbar(user_info) # <-- ★ 変更
            return dbc.Alert("無効なURLです。", color="danger"), create_navbar(user_info), no_update # ★ URLは更新しない

    # 通常ページのナビゲーションバー生成
    navbar = create_navbar(user_info)
    subjects = get_all_subjects() # 全科目リスト取得（初回ロード高速化のためここで取得）

    # 各ページへのルーティング
    if pathname == '/homework':
        page_content = create_homework_layout(user_info)
    elif pathname == '/past-exam':
        page_content = create_past_exam_layout() # 引数不要に変更
    elif pathname == '/root-table':
        page_content = create_root_table_layout(user_info)
    elif pathname == '/statistics':
        page_content = create_statistics_layout(user_info)
    elif pathname == '/howto':
        page_content = create_howto_layout(user_info)
    elif pathname == '/bug-report':
        page_content = create_bug_report_layout(user_info)
    elif pathname == '/changelog':
        page_content = create_changelog_layout()
    elif pathname == '/admin':
        # 管理者権限チェック
        if user_info.get('role') != 'admin':
            page_content = create_access_denied_layout()
        else:
            # 管理者ページレイアウト生成
            page_content = dbc.Container([
                html.H3("管理者メニュー", className="mt-4 mb-4"),
                # 各種削除確認ダイアログ
                dcc.ConfirmDialog(id='delete-user-confirm', message='本当にこのユーザーを削除しますか？関連する講師情報も削除されます。'),
                dcc.ConfirmDialog(id='delete-student-confirm', message='本当にこの生徒を削除しますか？関連する進捗・宿題・試験結果も全て削除されます。'),
                dcc.ConfirmDialog(id='delete-textbook-confirm', message='本当にこの参考書を削除しますか？宿題での関連付けは解除されます。'),
                dcc.ConfirmDialog(id='delete-preset-confirm', message='本当にこのプリセットを削除しますか？'),

                dbc.Row([
                    # --- 左列 ---
                    dbc.Col([
                        dbc.Card([dbc.CardBody([
                            html.H5("👥 ユーザー管理", className="card-title"),
                            html.P("ユーザーの追加・一覧・編集・削除を行います。", className="card-text small text-muted"),
                            dbc.Button("ユーザー一覧", id="user-list-btn", className="me-2"),
                            dbc.Button("新規ユーザー作成", id="new-user-btn", color="success")
                        ])], className="mb-3"),

                        dbc.Card([dbc.CardBody([
                            html.H5("🧑‍🎓 生徒管理", className="card-title"),
                            html.P("生徒情報の登録、編集、削除、担当講師の割り当てを行います。", className="card-text small text-muted"),
                            dbc.Button("生徒を編集", id="open-student-management-modal-btn", color="warning")
                        ])], className="mb-3"),

                        dbc.Card([dbc.CardBody([
                            html.H5("📚 参考書マスター管理", className="card-title"),
                            html.P("学習計画で使用する参考書のマスターデータを管理します。", className="card-text small text-muted"),
                            dbc.Button("マスターを編集", id="open-master-textbook-modal-btn", color="dark")
                        ])], className="mb-3"),

                    ], md=6),

                    # --- 右列 ---
                    dbc.Col([
                        dbc.Card([dbc.CardBody([
                            html.H5("📦 一括登録設定", className="card-title"),
                            html.P("学習計画の一括登録用プリセットを作成・編集します。", className="card-text small text-muted"),
                            dbc.Button("プリセットを編集", id="open-bulk-preset-modal-btn", color="secondary")
                        ])], className="mb-3"),

                        dbc.Card([dbc.CardBody([
                            html.H5("📢 更新履歴の管理", className="card-title"),
                            html.P("アプリケーションの更新履歴を追加します。", className="card-text small text-muted"),
                            dbc.Button("更新履歴を追加", id="add-changelog-btn", color="info")
                        ])], className="mb-3"),

                        dbc.Card([dbc.CardBody([
                            html.H5("📊 模試結果一覧", className="card-title"),
                            html.P("校舎全体の模試結果を一覧表示・検索します。", className="card-text small text-muted"),
                            dbc.Button("模試結果一覧を表示", id="open-mock-exam-list-modal-btn", color="primary")
                        ])], className="mb-3"),
                    ], md=6),
                ]),

                html.Div(id="admin-statistics", className="mt-4"), # 統計表示エリア
                # 管理者用モーダルコンポーネント
                create_master_textbook_modal(), create_textbook_edit_modal(),
                create_student_management_modal(), create_student_edit_modal(),
                create_bulk_preset_management_modal(), create_bulk_preset_edit_modal(),
                create_user_list_modal(),
                create_new_user_modal(),
                create_user_edit_modal(),
                create_add_changelog_modal(),
                create_mock_exam_list_modal()
            ], fluid=True) # Container fluid=True に変更
    else: # デフォルトはダッシュボードページ
        page_content = html.Div([
            create_main_layout(user_info),
            create_root_table_layout(user_info),
            *create_all_modals(subjects) # 学習計画モーダルなどを生成
        ])

    # 生成したページコンテンツとナビゲーションバーを返す
    # return page_content, navbar # <-- ★ 変更
    return page_content, navbar, no_update # ★ URLは更新しない


# --- 管理者統計コールバック ---
@app.callback(
    Output('admin-statistics', 'children'),
    Input('url', 'pathname') # URL変更時に統計を更新
)
def update_admin_statistics(pathname):
    """管理者ページの統計情報をデータベースから取得して更新"""
    # 管理者ページ以外では何もしない
    if pathname != '/admin':
        return ""

    try:
        # データアクセス層の関数を呼び出す
        student_counts = get_student_count_by_school()
        textbook_counts = get_textbook_count_by_subject()

        # データがあればDataFrameを作成、なければ空のDataFrame
        df_students = pd.DataFrame(student_counts) if student_counts else pd.DataFrame(columns=['school', 'count'])
        df_textbooks = pd.DataFrame(textbook_counts) if textbook_counts else pd.DataFrame(columns=['subject', 'count'])

        # カラム名を日本語に変更
        df_students.columns = ["校舎", "生徒数"]
        df_textbooks.columns = ["科目", "参考書数"]

        # DataFrameからテーブルを生成
        student_table = dbc.Table.from_dataframe(df_students, striped=True, bordered=True, hover=True, size="sm")
        textbook_table = dbc.Table.from_dataframe(df_textbooks, striped=True, bordered=True, hover=True, size="sm")

        # レイアウトを返す
        return dbc.Row([
            dbc.Col(dbc.Card([dbc.CardHeader("🏫 校舎ごとの生徒数"), dbc.CardBody(student_table)]), width=6, className="mb-3"),
            dbc.Col(dbc.Card([dbc.CardHeader("📚 科目ごとの参考書数"), dbc.CardBody(textbook_table)]), width=6, className="mb-3")
        ])
    except Exception as e:
        print(f"管理者統計の取得エラー: {e}") # エラーログ
        return dbc.Alert(f"統計情報の取得に失敗しました: {e}", color="danger")

# --- トースト通知コールバック ---
@app.callback(
    [Output('success-toast', 'is_open'),
     Output('success-toast', 'children')],
    Input('toast-trigger', 'data'),
    prevent_initial_call=True
)
def show_success_toast(toast_data):
    """成功時にトーストを表示する"""
    if toast_data and 'message' in toast_data:
        # タイムスタンプを削除 (表示には不要)
        message = toast_data['message']
        return True, message
    return False, ""

# --- コールバック登録 ---
register_auth_callbacks(app)
register_main_callbacks(app)
register_progress_callbacks(app)
register_admin_callbacks(app)
register_report_callbacks(app)
register_homework_callbacks(app)
register_plan_callbacks(app)
register_past_exam_callbacks(app) # 過去問・入試・模試コールバック
register_bug_report_callbacks(app)
register_statistics_callbacks(app)
register_root_table_callbacks(app)

# === APIエンドポイント ===

# --- 生徒ID取得API (変更なし) ---
@server.route('/api/get-student-id', methods=['GET'])
def get_student_id_by_name():
    auth_key = request.headers.get('X-API-KEY')
    if auth_key != API_KEY:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    school = request.args.get('school')
    name = request.args.get('name')
    if not school or not name:
        return jsonify({"success": False, "message": "Missing 'school' or 'name' query parameter"}), 400
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT id FROM students WHERE school = %s AND name = %s", (school, name))
            student = cur.fetchone()
        if student: return jsonify({"success": True, "student_id": student['id']}), 200
        else: return jsonify({"success": False, "message": "Student not found"}), 404
    except (Exception, psycopg2.Error) as e:
        print(f"Error processing /api/get-student-id: {e}")
        return jsonify({"success": False, "message": "An internal error occurred"}), 500
    finally:
        if conn: conn.close()

# --- 過去問結果送信API (変更なし) ---
@server.route('/api/submit-past-exam', methods=['POST'])
def submit_past_exam_result():
    auth_key = request.headers.get('X-API-KEY')
    if auth_key != API_KEY:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        data = request.get_json()
        print(f"Received past exam data via API: {data}") # ログ出力
        required_fields = ['student_id', 'date', 'university_name', 'year', 'subject', 'total_questions']
        if not all(field in data for field in required_fields):
            print(f"Missing required fields in past exam data: { {f for f in required_fields if f not in data} }")
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        try:
            student_id = int(data['student_id'])
            year = int(data['year'])
            total_questions = int(data['total_questions']) if data.get('total_questions') is not None else None
            correct_answers = int(data['correct_answers']) if data.get('correct_answers') is not None else None
            time_required = int(data['time_required']) if data.get('time_required') is not None else None
            total_time_allowed = int(data['total_time_allowed']) if data.get('total_time_allowed') is not None else None
            date_val = datetime.strptime(str(data['date']), '%Y-%m-%d').date() # dateオブジェクトに
        except (ValueError, TypeError) as e:
            print(f"Data conversion error in past exam API: {e}")
            return jsonify({"success": False, "message": f"Invalid data format: {e}"}), 400
        result_data = {
            'date': date_val, 'university_name': data['university_name'],
            'faculty_name': data.get('faculty_name'), 'exam_system': data.get('exam_system'),
            'year': year, 'subject': data['subject'], 'time_required': time_required,
            'total_time_allowed': total_time_allowed, 'correct_answers': correct_answers,
            'total_questions': total_questions }
        success, message = add_past_exam_result(student_id, result_data)
        if success: return jsonify({"success": True, "message": message}), 200
        else: return jsonify({"success": False, "message": message}), 500
    except json.JSONDecodeError: return jsonify({"success": False, "message": "Invalid JSON data"}), 400
    except Exception as e: print(f"Error processing /api/submit-past-exam: {e}"); return jsonify({"success": False, "message": "An internal error occurred"}), 500

# --- 入試結果送信API (変更なし) ---
@server.route('/api/submit-acceptance', methods=['POST'])
def submit_acceptance_result():
    auth_key = request.headers.get('X-API-KEY')
    if auth_key != API_KEY: return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        data = request.get_json(); print(f"Received acceptance data via API: {data}")
        required_fields = ['student_id', 'university_name', 'faculty_name']
        if not all(field in data for field in required_fields): print(f"Missing required fields in acceptance data: { {f for f in required_fields if f not in data} }"); return jsonify({"success": False, "message": "Missing required fields"}), 400
        try:
            student_id = int(data['student_id'])
            date_fields = ['application_deadline', 'exam_date', 'announcement_date', 'procedure_deadline']
            result_data = { 'university_name': data['university_name'], 'faculty_name': data['faculty_name'], 'department_name': data.get('department_name'), 'exam_system': data.get('exam_system'), 'result': data.get('result') }
            for field in date_fields:
                if data.get(field): result_data[field] = datetime.strptime(str(data[field]), '%Y-%m-%d').date() # dateオブジェクトに
                else: result_data[field] = None
        except (ValueError, TypeError) as e: print(f"Data conversion error in acceptance API: {e}"); return jsonify({"success": False, "message": f"Invalid data format: {e}"}), 400
        success, message = add_acceptance_result(student_id, result_data)
        if success: return jsonify({"success": True, "message": message}), 200
        else: return jsonify({"success": False, "message": message}), 500
    except json.JSONDecodeError: return jsonify({"success": False, "message": "Invalid JSON data"}), 400
    except Exception as e: print(f"Error processing /api/submit-acceptance: {e}"); return jsonify({"success": False, "message": "An internal error occurred"}), 500

# ★★★ 模試結果送信APIを追加 ★★★
@server.route('/api/submit-mock-exam', methods=['POST'])
def submit_mock_exam_result():
    # APIキーの検証
    auth_key = request.headers.get('X-API-KEY')
    if auth_key != API_KEY:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        data = request.get_json()
        print(f"Received mock exam data via API: {data}") # ログ出力

        # --- 必須項目の検証 ---
        # Googleフォームからの項目名に合わせて調整が必要な場合がある
        # ここでは、キーがDBカラム名と（ほぼ）一致すると仮定
        required_fields = ['student_id', 'result_type', 'mock_exam_name', 'mock_exam_format', 'grade', 'round']
        missing_fields = [f for f in required_fields if f not in data or not data[f]]
        if missing_fields:
             print(f"Missing required fields in mock exam data: {missing_fields}")
             return jsonify({"success": False, "message": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        # --- student_id の数値変換 ---
        try:
            student_id = int(data['student_id'])
        except (ValueError, TypeError):
             print(f"Invalid student_id format: {data.get('student_id')}")
             return jsonify({"success": False, "message": "Invalid student_id format"}), 400

        # --- データ整形 ---
        # add_mock_exam_result 関数内で型変換やNone処理を行うため、ここでは必須項目の存在確認のみ
        # 必要であれば、ここでさらに詳細なバリデーションや整形を行う
        # 例：日付形式の事前チェックなど
        if data.get('exam_date'):
            try:
                datetime.strptime(str(data['exam_date']), '%Y-%m-%d')
            except (ValueError, TypeError):
                 print(f"Invalid exam_date format: {data.get('exam_date')}")
                 return jsonify({"success": False, "message": "Invalid exam_date format (YYYY-MM-DD expected)"}), 400

        # --- データベースへの保存 ---
        # data 辞書をそのまま渡す (add_mock_exam_result内で処理)
        success, message = add_mock_exam_result(student_id, data)

        if success:
            return jsonify({"success": True, "message": message}), 200
        else:
            # add_mock_exam_result内でエラーログが出るはず
            return jsonify({"success": False, "message": message}), 500

    except json.JSONDecodeError:
        print("Invalid JSON received for mock exam")
        return jsonify({"success": False, "message": "Invalid JSON data"}), 400
    except Exception as e:
        print(f"Error processing /api/submit-mock-exam: {e}") # エラーログ
        return jsonify({"success": False, "message": "An internal error occurred"}), 500
# ★★★ ここまで追加 ★★★


# --- アプリケーションの実行 ---
if __name__ == '__main__':
    # このブロックは 'python app_main.py' で直接実行したときのみ動作
    print(
        f"🚀 アプリケーションを開発モードで起動中... http://{APP_CONFIG['server']['host']}:{APP_CONFIG['server']['port']}"
    )
    # Gunicornではなく、開発用のサーバーで実行
    app.run(
        debug=APP_CONFIG['server']['debug'],
        host=APP_CONFIG['server']['host'],
        port=APP_CONFIG['server']['port']
    )