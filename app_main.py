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

# --- プロジェクトのルートディレクトリをPythonのパスに追加 ---
# これにより、どのファイルからでも 'components' や 'data' などを正しくインポートできるようになります。
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


# --- 設定と外部ファイルのインポート ---
from config.settings import APP_CONFIG
from config.styles import APP_INDEX_STRING, EXTERNAL_STYLESHEETS
from data.nested_json_processor import initialize_user_data, get_all_subjects
from components.main_layout import create_main_layout, create_navbar
from components.modals import create_all_modals
from components.login_components import (
    create_login_layout,
    create_access_denied_layout,
    create_user_profile_modal, create_password_change_modal
)
from callbacks.main_callbacks import register_main_callbacks
from callbacks.progress_callbacks import register_progress_callbacks
from callbacks.student_callbacks import register_student_callbacks
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

# データベースファイル名
DATABASE_FILE = 'progress.db'

# --- メインレイアウト ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=True), # refreshをTrueに変更
    dcc.Store(id='auth-store', storage_type='session'),
    
    # ★ 不要になったupdate-trigger-storeを削除し、以下2行を追加
    dcc.Store(id='school-selection-store', storage_type='session'),
    dcc.Store(id='student-selection-store', storage_type='session'),
    
    html.Div(id='page-content'),

    # 認証関連のモーダル
    create_user_profile_modal(),
    create_password_change_modal(),
    # PDFダウンロード用のコンポーネント
    dcc.Download(id="download-pdf-report")
])

# --- ヘルパー関数 ---
def get_current_user_from_store(auth_store_data):
    """auth-storeからユーザー情報を取得する"""
    return auth_store_data if auth_store_data and isinstance(auth_store_data, dict) else None

# --- ページ表示コールバック（ルーティング） ---
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname'),
     Input('auth-store', 'data')]
)
def display_page(pathname, auth_store_data):
    """URLのパスに応じてページコンテンツを切り替え"""
    user_info = get_current_user_from_store(auth_store_data)

    if pathname == '/login':
        return create_login_layout()

    if not user_info:
        return create_login_layout()

    initialize_user_data(user_info['username'])
    subjects = get_all_subjects()

    if pathname in ['/', None]:
        return html.Div([
            create_main_layout(user_info),
            *create_all_modals(subjects),
            dbc.Toast(
                id="success-toast", header="成功", is_open=False, dismissable=True,
                duration=3000, icon="success",
                style={
                    "position": "fixed", "top": 66, "right": 10,
                    "width": 350, "zIndex": 1050
                },
            ),
        ])

    if pathname == '/admin':
        if user_info.get('role') != 'admin':
            return html.Div([create_navbar(user_info), create_access_denied_layout()])

        return html.Div([
            create_navbar(user_info),
            dbc.Container([
                html.H1("🔧 管理者メニュー", className="mt-4"),
                dbc.Row([
                    dbc.Col(dbc.Card([
                        dbc.CardHeader("👥 ユーザー管理"),
                        dbc.CardBody([
                            dbc.Button("ユーザー一覧", id="user-list-btn", className="me-2"),
                            dbc.Button("新規ユーザー作成", id="new-user-btn", color="success")
                        ])
                    ]), width=6),
                    dbc.Col(dbc.Card([
                        dbc.CardHeader("💾 データ管理"),
                        dbc.CardBody(dbc.Button("JSONバックアップ", id="backup-btn", color="warning"))
                    ]), width=6)
                ], className="mb-4"),
                html.Div(id="admin-statistics")
            ])
        ])

    return create_main_layout(user_info)

# --- 管理者向け統計情報コールバック ---
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


# --- コールバック登録 ---
register_auth_callbacks(app)
register_main_callbacks(app, None)
register_progress_callbacks(app, None)
register_student_callbacks(app, None)
register_admin_callbacks(app, None)
register_report_callbacks(app)
register_homework_callbacks(app)
register_plan_callbacks(app)

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