# app_main.py

#!/usr/bin/env python3
"""
学習進捗ダッシュボード - データベース版 認証機能付きメインアプリケーション
"""
import sys
import os
import threading
import time
import webbrowser
import sqlite3
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import datetime # datetimeをインポート
from components.past_exam_layout import create_past_exam_layout
from callbacks.past_exam_callbacks import register_past_exam_callbacks

# --- プロジェクトのルートディレクトリをPythonのパスに追加 ---
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


# --- 設定と外部ファイルのインポート ---
from config.settings import APP_CONFIG
from config.styles import APP_INDEX_STRING, EXTERNAL_STYLESHEETS
from data.nested_json_processor import get_all_subjects
from components.main_layout import create_main_layout, create_navbar
from components.homework_layout import create_homework_layout
from components.modals import create_all_modals
from components.admin_components import (
    create_master_textbook_modal, create_textbook_edit_modal,
    create_student_edit_modal, create_student_management_modal,
    create_bulk_preset_management_modal, create_bulk_preset_edit_modal
)
from components.login_components import (
    create_login_layout,
    create_access_denied_layout,
    create_user_profile_modal, create_password_change_modal
)
from callbacks.main_callbacks import register_main_callbacks
from callbacks.progress_callbacks import register_progress_callbacks
from callbacks.admin_callbacks import register_admin_callbacks
from callbacks.auth_callbacks import register_auth_callbacks
from callbacks.homework_callbacks import register_homework_callbacks
from callbacks.report_callbacks import register_report_callbacks
from callbacks.plan_callbacks import register_plan_callbacks

# --- アプリケーションの初期化 ---
app = dash.Dash(
    __name__,
    external_stylesheets=EXTERNAL_STYLESHEETS,
    suppress_callback_exceptions=True,
    title="学習進捗ダッシュボード"
)
app.index_string = APP_INDEX_STRING
app.server.secret_key = APP_CONFIG['server']['secret_key']

DATABASE_FILE = 'progress.db'

# --- メインレイアウト ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=True),
    dcc.Store(id='auth-store', storage_type='session'),
    dcc.Store(id='school-selection-store', storage_type='session'),
    dcc.Store(id='student-selection-store', storage_type='session'),
    dcc.Store(id='admin-update-trigger', storage_type='memory'),
    # --- ★★★ ここから修正 ★★★ ---
    dcc.Store(id='toast-trigger', storage_type='memory'), # IDを 'toast-trigger' に変更
    # --- ★★★ ここまで修正 ★★★ ---

    # --- グローバルなコンポーネント ---
    html.Div(id='navbar-container'), # ナビゲーションバー用のコンテナ

    dbc.Container([
        # 校舎と生徒のセレクターをページコンテンツの外（共通部分）に配置
        html.Div(id='school-dropdown-container'),
        html.Div(id='student-dropdown-container', className="mb-3"),
        
        # ページ固有のコンテンツがここに表示される
        html.Div(id='page-content'),
    ], fluid=True, className="mt-4"),

    # --- 通知用トースト ---
    dbc.Toast(
        id="success-toast", header="成功", is_open=False, dismissable=True,
        icon="success", duration=4000,
        style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 9999},
    ),
    # 認証関連のモーダル
    create_user_profile_modal(),
    create_password_change_modal(),
    dcc.Download(id="download-pdf-report")
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
        # 未ログイン時はログイン画面のみ表示し、ナビゲーションバーは非表示
        return create_login_layout(), None

    # ログイン済みユーザーには常にナビゲーションバーを表示
    navbar = create_navbar(user_info)
    subjects = get_all_subjects()

    if pathname == '/homework':
        page_content = create_homework_layout(user_info)
        return page_content, navbar
    
    if pathname == '/past-exam':
        page_content = create_past_exam_layout()
        return page_content, navbar

    if pathname == '/admin':
        if user_info.get('role') != 'admin':
            return create_access_denied_layout(), navbar

        page_content = dbc.Container([
            html.H1("🔧 管理者メニュー", className="mt-4"),
            dbc.Row([
                dbc.Col(dbc.Card([dbc.CardHeader("👥 ユーザー管理"), dbc.CardBody([dbc.Button("ユーザー一覧", id="user-list-btn", className="me-2"), dbc.Button("新規ユーザー作成", id="new-user-btn", color="success")])]), width=12, md=4, lg=3, className="mb-3"),
                dbc.Col(dbc.Card([dbc.CardHeader("🧑‍🎓 生徒管理"), dbc.CardBody(dbc.Button("生徒を編集", id="open-student-management-modal-btn", color="info", className="w-100"))]), width=12, md=4, lg=3, className="mb-3"),
                dbc.Col(dbc.Card([dbc.CardHeader("📚 参考書マスター管理"), dbc.CardBody(dbc.Button("マスターを編集", id="open-master-textbook-modal-btn", color="primary", className="w-100"))]), width=12, md=4, lg=3, className="mb-3"),
                dbc.Col(dbc.Card([dbc.CardHeader("📦 一括登録設定"), dbc.CardBody(dbc.Button("プリセットを編集", id="open-bulk-preset-modal-btn", color="secondary", className="w-100"))]), width=12, md=4, lg=3, className="mb-3"),
                dbc.Col(dbc.Card([dbc.CardHeader("💾 データ管理"), dbc.CardBody(dbc.Button("JSONバックアップ", id="backup-btn", color="warning", className="w-100"))]), width=12, md=4, lg=3, className="mb-3")
            ], className="mb-4"),
            html.Div(id="admin-statistics"),
            create_master_textbook_modal(), create_textbook_edit_modal(),
            create_student_management_modal(), create_student_edit_modal(),
            create_bulk_preset_management_modal(), create_bulk_preset_edit_modal(),
        ])
        return page_content, navbar
    
    # デフォルトはホーム画面
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
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        total_students = cursor.execute('SELECT COUNT(id) FROM students').fetchone()[0]
        total_subjects = cursor.execute('SELECT COUNT(DISTINCT subject) FROM progress').fetchone()[0]
        total_books = cursor.execute('SELECT COUNT(id) FROM progress').fetchone()[0]
        completed_books = cursor.execute('SELECT COUNT(id) FROM progress WHERE is_done = 1').fetchone()[0]
        conn.close()

        return dbc.Card([
            dbc.CardHeader("📊 システム統計情報"),
            dbc.CardBody(dbc.Row([
                dbc.Col([html.H4(total_students), html.P("総生徒数")], width=3),
                dbc.Col([html.H4(total_subjects), html.P("総科目数")], width=3),
                dbc.Col([html.H4(total_books), html.P("総参考書数")], width=3),
                dbc.Col([html.H4(completed_books), html.P("完了参考書数")], width=3)
            ]))
        ])
    except sqlite3.Error as e:
        return dbc.Alert(f"統計情報の取得に失敗しました: {e}", color="danger")

# --- ★★★ ここから修正 ★★★ ---
@app.callback(
    [Output('success-toast', 'is_open'),
     Output('success-toast', 'children')],
    Input('toast-trigger', 'data'), # IDを 'toast-trigger' に変更
    prevent_initial_call=True
)
def show_success_toast(toast_data):
    """成功時にトーストを表示する"""
    if toast_data and 'message' in toast_data:
        return True, toast_data['message']
    return False, ""
# --- ★★★ ここまで修正 ★★★ ---

# --- コールバック登録 ---
register_auth_callbacks(app)
register_main_callbacks(app)
register_progress_callbacks(app)
register_admin_callbacks(app)
register_report_callbacks(app)
register_homework_callbacks(app)
register_plan_callbacks(app)
register_past_exam_callbacks(app)

# --- ブラウザ自動起動 ---
def open_browser():
    """開発用にブラウザを自動で開く"""
    time.sleep(2)
    webbrowser.open(f"http://{APP_CONFIG['server']['host']}:{APP_CONFIG['server']['port']}")


# --- アプリケーション実行 ---
if __name__ == '__main__':
    print(
        f"🚀 アプリケーションを起動中... http://{APP_CONFIG['server']['host']}:{APP_CONFIG['server']['port']}"
    )
    if APP_CONFIG['browser']['auto_open']:
        threading.Thread(target=open_browser, daemon=True).start()

    app.run(
        debug=APP_CONFIG['server']['debug'],
        use_reloader=False,
        host=APP_CONFIG['server']['host'],
        port=APP_CONFIG['server']['port']
    )