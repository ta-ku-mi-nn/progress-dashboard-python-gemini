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
from dash import dcc, html, Input, Output
import plotly.io as pio
from flask import request, jsonify # Flaskのrequestとjsonifyを追加
import json # jsonを追加
from data.nested_json_processor import get_db_connection
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime

# --- グラフ描画の安定化のため、デフォルトテンプレートを設定 ---
pio.templates.default = "plotly_white"

# --- プロジェクトのルートディレクトリをPythonのパスに追加 ---
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


# --- 設定と外部ファイルのインポート ---
from config.settings import APP_CONFIG
from config.styles import APP_INDEX_STRING, EXTERNAL_STYLESHEETS
from data.nested_json_processor import (
    get_all_subjects, get_student_info_by_id,
    get_student_count_by_school, get_textbook_count_by_subject
)
from components.main_layout import create_main_layout, create_navbar
from components.homework_layout import create_homework_layout
from components.modals import create_all_modals
from components.admin_components import (
    create_master_textbook_modal, create_textbook_edit_modal,
    create_student_edit_modal, create_student_management_modal,
    create_bulk_preset_management_modal, create_bulk_preset_edit_modal,
    create_user_edit_modal,
    create_add_changelog_modal
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
from components.statistics_layout import create_statistics_layout # 追加
from callbacks.statistics_callbacks import register_statistics_callbacks # 追加
from data.nested_json_processor import add_past_exam_result, add_acceptance_result

API_KEY = "YOUR_SECRET_API_KEY"  # 適切なAPIキーに置き換えてください

# --- アプリケーションの初期化 ---
app = dash.Dash(
    __name__,
    external_stylesheets=EXTERNAL_STYLESHEETS,
    suppress_callback_exceptions=True,
    title="学習進捗ダッシュボード"
)
app.index_string = APP_INDEX_STRING
app.server.secret_key = APP_CONFIG['server']['secret_key']
server = app.server

# --- メインレイアウト ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=True),
    dcc.Store(id='auth-store', storage_type='session'),
    dcc.Store(id='school-selection-store', storage_type='session'),
    dcc.Store(id='student-selection-store', storage_type='session'),
    dcc.Store(id='admin-update-trigger', storage_type='memory'),
    dcc.Store(id='toast-trigger', storage_type='memory'),
    dcc.Store(id='item-to-delete-store', storage_type='memory'),
    dcc.Store(id='save-status-result-store', storage_type='memory'),

    html.Div(id='dummy-clientside-output', style={'display': 'none'}),
    dcc.Store(id='report-content-store', storage_type='session'),
    html.Div(id='navbar-container'),

    dbc.Container([
        html.Div(id='school-dropdown-container'),
        html.Div(id='student-dropdown-container', className="mb-3"),
        html.Div(id='page-content'),
    ], fluid=True, className="mt-4"),

    dbc.Toast(
        id="success-toast", header="成功", is_open=False, dismissable=True,
        icon="success", duration=4000,
        style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 9999},
    ),
    create_user_profile_modal(),
    create_password_change_modal(),
    dcc.Download(id="download-pdf-report"),
    dcc.Download(id="download-backup")
])

# --- ヘルパー関数 ---
def get_current_user_from_store(auth_store_data):
    return auth_store_data if auth_store_data and isinstance(auth_store_data, dict) else None

# --- ページ表示コールバック（ルーティング） ---
@app.callback(
    [Output('page-content', 'children'),
     Output('navbar-container', 'children')],
    [Input('url', 'pathname'),
     Input('auth-store', 'data')]
)
def display_page(pathname, auth_store_data):
    """URLのパスに応じてページコンテンツとナビゲーションバーを切り替え"""
    user_info = get_current_user_from_store(auth_store_data)

    if not user_info:
        return create_login_layout(), None

    if pathname.startswith('/report/'):
        try:
            student_id = int(pathname.split('/')[-1])
            student_info = get_student_info_by_id(student_id)
            student_name = student_info.get('name', '不明な生徒')
            # レポートページではナビゲーションバーを非表示にします
            return create_report_layout(student_name), None
        except (ValueError, IndexError):
            return dbc.Alert("無効な生徒IDです。", color="danger"), create_navbar(user_info)

    navbar = create_navbar(user_info)
    subjects = get_all_subjects()

    if pathname == '/homework':
        page_content = create_homework_layout(user_info)
        return page_content, navbar

    if pathname == '/past-exam':
        page_content = create_past_exam_layout()
        return page_content, navbar

    if pathname == '/statistics': # このブロックを追加
        page_content = create_statistics_layout()
        return page_content, navbar

    if pathname == '/howto':
        return create_howto_layout(user_info), navbar

    if pathname == '/bug-report':
        return create_bug_report_layout(user_info), navbar

    if pathname == '/changelog':
        return create_changelog_layout(), navbar

    if pathname == '/admin':
        if user_info.get('role') != 'admin':
            return create_access_denied_layout(), navbar

        page_content = dbc.Container([
            html.H3("管理者メニュー", className="mt-4 mb-4"),
            dcc.ConfirmDialog(id='delete-user-confirm', message='本当にこのユーザーを削除しますか？'),
            dcc.ConfirmDialog(id='delete-student-confirm', message='本当にこの生徒を削除しますか？'),
            dcc.ConfirmDialog(id='delete-textbook-confirm', message='本当にこの参考書を削除しますか？'),
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
                        html.P("生徒情報の登録、編集、削除を行います。", className="card-text small text-muted"),
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
                        html.H5("💾 データバックアップ", className="card-title"),
                        html.P("データベースの全データをJSONファイルとしてダウンロードします。", className="card-text small text-muted"),
                        dbc.Button("バックアップを実行", id="backup-btn", color="primary")
                    ])], className="mb-3"),
                ], md=6),
            ]),

            html.Div(id="admin-statistics", className="mt-4"),
            create_master_textbook_modal(), create_textbook_edit_modal(),
            create_student_management_modal(), create_student_edit_modal(),
            create_bulk_preset_management_modal(), create_bulk_preset_edit_modal(),
            create_user_list_modal(),
            create_new_user_modal(),
            create_user_edit_modal(),
            create_add_changelog_modal()
        ])
        return page_content, navbar

    page_content = html.Div([
        create_main_layout(user_info),
        *create_all_modals(subjects)
    ])
    return page_content, navbar

@app.callback(
    Output('admin-statistics', 'children'),
    Input('url', 'pathname')
)
def update_admin_statistics(pathname):
    """管理者ページの統計情報をデータベースから取得して更新"""
    if pathname != '/admin':
        return ""

    try:
        # データアクセス層の関数を呼び出すように変更
        student_counts = get_student_count_by_school()
        textbook_counts = get_textbook_count_by_subject()

        student_table = dbc.Table.from_dataframe(pd.DataFrame(student_counts), striped=True, bordered=True, hover=True)
        textbook_table = dbc.Table.from_dataframe(pd.DataFrame(textbook_counts), striped=True, bordered=True, hover=True)

        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🏫 校舎ごとの生徒数"),
                    dbc.CardBody(student_table)
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📚 科目ごとの参考書数"),
                    dbc.CardBody(textbook_table)
                ])
            ], width=6)
        ])
    except Exception as e:
        return dbc.Alert(f"統計情報の取得に失敗しました: {e}", color="danger")

@app.callback(
    [Output('success-toast', 'is_open'),
     Output('success-toast', 'children')],
    Input('toast-trigger', 'data'),
    prevent_initial_call=True
)
def show_success_toast(toast_data):
    """成功時にトーストを表示する"""
    if toast_data and 'message' in toast_data:
        return True, toast_data['message']
    return False, ""

# --- コールバック登録 ---
register_auth_callbacks(app)
register_main_callbacks(app)
register_progress_callbacks(app)
register_admin_callbacks(app)
register_report_callbacks(app)
register_homework_callbacks(app)
register_plan_callbacks(app)
register_past_exam_callbacks(app)
register_bug_report_callbacks(app)
register_statistics_callbacks(app) # この行を追加

# === APIエンドポイントを追加 ===
@server.route('/api/get-student-id', methods=['GET'])
def get_student_id_by_name():
    # APIキーの検証
    auth_key = request.headers.get('X-API-KEY')
    if auth_key != API_KEY:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    # クエリパラメータから校舎名と生徒名を取得
    school = request.args.get('school')
    name = request.args.get('name')

    if not school or not name:
        return jsonify({"success": False, "message": "Missing 'school' or 'name' query parameter"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT id FROM students WHERE school = %s AND name = %s",
                (school, name)
            )
            student = cur.fetchone()

        if student:
            return jsonify({"success": True, "student_id": student['id']}), 200
        else:
            return jsonify({"success": False, "message": "Student not found"}), 404

    except (Exception, psycopg2.Error) as e:
        print(f"Error processing /api/get-student-id: {e}")
        # conn.rollback() # SELECT文なので通常ロールバックは不要
        return jsonify({"success": False, "message": "An internal error occurred"}), 500
    finally:
        if conn:
            conn.close()

@server.route('/api/submit-past-exam', methods=['POST'])
def submit_past_exam_result():
    # APIキーの検証 (簡易的な例)
    auth_key = request.headers.get('X-API-KEY')
    if auth_key != API_KEY:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        data = request.get_json()
        print(f"Received past exam data: {data}") # ログ出力（デバッグ用）

        # --- データの検証 ---
        required_fields = ['student_id', 'date', 'university_name', 'year', 'subject', 'total_questions']
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        # --- データの整形 ---
        # GASから送られてくるデータ形式に合わせて調整が必要な場合があります
        # 例: total_questions, correct_answers が文字列で送られてくる場合、数値に変換
        try:
            student_id = int(data['student_id']) # ダッシュボード側の生徒IDに変換が必要な場合がある
            year = int(data['year'])
            total_questions = int(data['total_questions'])
            correct_answers = int(data['correct_answers']) if data.get('correct_answers') else None
            time_required = int(data['time_required']) if data.get('time_required') else None
            total_time_allowed = int(data['total_time_allowed']) if data.get('total_time_allowed') else None
            # 日付形式の確認・変換 (YYYY-MM-DD を想定)
            date_val = datetime.strptime(data['date'], '%Y-%m-%d').strftime('%Y-%m-%d')
        except (ValueError, TypeError) as e:
            print(f"Data conversion error: {e}")
            return jsonify({"success": False, "message": f"Invalid data format: {e}"}), 400

        result_data = {
            'date': date_val,
            'university_name': data['university_name'],
            'faculty_name': data.get('faculty_name'),
            'exam_system': data.get('exam_system'),
            'year': year,
            'subject': data['subject'],
            'time_required': time_required,
            'total_time_allowed': total_time_allowed,
            'correct_answers': correct_answers,
            'total_questions': total_questions
        }

        # --- データベースへの保存 ---
        success, message = add_past_exam_result(student_id, result_data)

        if success:
            return jsonify({"success": True, "message": message}), 200
        else:
            return jsonify({"success": False, "message": message}), 500

    except json.JSONDecodeError:
        return jsonify({"success": False, "message": "Invalid JSON data"}), 400
    except Exception as e:
        print(f"Error processing /api/submit-past-exam: {e}") # エラーログ
        return jsonify({"success": False, "message": "An internal error occurred"}), 500

@server.route('/api/submit-acceptance', methods=['POST'])
def submit_acceptance_result():
    # APIキーの検証
    auth_key = request.headers.get('X-API-KEY')
    if auth_key != API_KEY:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        data = request.get_json()
        print(f"Received acceptance data: {data}")

        # --- データの検証 ---
        required_fields = ['student_id', 'university_name', 'faculty_name']
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "Missing required fields (student_id, university_name, faculty_name)"}), 400

        # --- データの整形 ---
        try:
            student_id = int(data['student_id'])
            # 日付フィールドが存在すれば形式チェック (YYYY-MM-DD を想定)
            date_fields = ['application_deadline', 'exam_date', 'announcement_date', 'procedure_deadline']
            result_data = {
                'university_name': data['university_name'],
                'faculty_name': data['faculty_name'],
                'department_name': data.get('department_name'),
                'exam_system': data.get('exam_system'),
                'result': data.get('result'), # GAS側で合否も入力する場合
            }
            for field in date_fields:
                if data.get(field):
                    result_data[field] = datetime.strptime(data[field], '%Y-%m-%d').strftime('%Y-%m-%d')
                else:
                    result_data[field] = None # フィールドがない場合はNone

        except (ValueError, TypeError) as e:
             print(f"Data conversion error: {e}")
             return jsonify({"success": False, "message": f"Invalid data format: {e}"}), 400

        # --- データベースへの保存 ---
        # 注意: add_acceptance_result は result を引数に取らない場合があるので、
        # 必要に応じて data/nested_json_processor.py の関数を修正するか、
        # ここで result を除外する
        # （現在の add_acceptance_result は result を受け取るのでそのまま）
        success, message = add_acceptance_result(student_id, result_data)

        if success:
            return jsonify({"success": True, "message": message}), 200
        else:
            return jsonify({"success": False, "message": message}), 500

    except json.JSONDecodeError:
        return jsonify({"success": False, "message": "Invalid JSON data"}), 400
    except Exception as e:
        print(f"Error processing /api/submit-acceptance: {e}")
        return jsonify({"success": False, "message": "An internal error occurred"}), 500

if __name__ == '__main__':
    # このブロックは 'python app_main.py' で実行したときのみ動作
    print(
        f"🚀 アプリケーションを開発モードで起動中... http://{APP_CONFIG['server']['host']}:{APP_CONFIG['server']['port']}"
    )
    app.run(
        debug=APP_CONFIG['server']['debug'],
        host=APP_CONFIG['server']['host'],
        port=APP_CONFIG['server']['port']
    )