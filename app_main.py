#!/usr/bin/env python3
"""
学習進捗ダッシュボード - JSON版認証機能付きメインアプリケーション
"""
import threading
import time
import webbrowser
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output

# --- 設定と外部ファイルのインポート ---
from config.settings import APP_CONFIG
from config.styles import APP_INDEX_STRING, EXTERNAL_STYLESHEETS
from data.nested_json_processor import load_json_data, initialize_user_data, get_all_subjects
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

# --- アプリケーションの初期化 ---
app = dash.Dash(
    __name__,
    external_stylesheets=EXTERNAL_STYLESHEETS,
    suppress_callback_exceptions=True,
    title="学習進捗ダッシュボード"
)
app.index_string = APP_INDEX_STRING
app.server.secret_key = APP_CONFIG['server']['secret_key']

# --- データ読み込み ---
print("📊 全学習データを読み込んでいます...")
ALL_DATA = load_json_data()
if not ALL_DATA:
    print("⚠️ 警告: データファイルが見つからないか、内容が空です。")
else:
    print("✅ データ読み込み完了。")

# --- メインレイアウト ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='auth-store', storage_type='session'),
    dcc.Store(id='update-trigger-store'),  # データ更新のトリガー用
    html.Div(id='page-content'),

    # 認証関連のモーダル
    create_user_profile_modal(),
    create_password_change_modal(),
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

    # ログインしていない場合はログインページにリダイレクト
    if not user_info:
        return create_login_layout()

    # 新規ユーザー向けのデータ初期化（現在はプレースホルダー）
    initialize_user_data(user_info['username'])

    subjects = get_all_subjects(ALL_DATA)

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
                dbc.Alert([
                    html.H5("📊 システム情報"),
                    html.P(f"データファイル: {APP_CONFIG['data']['json_file']}"),
                ], color="info", className="mb-4"),
                dbc.Row([
                    dbc.Col(dbc.Card([
                        dbc.CardHeader("👥 ユーザー管理"),
                        dbc.CardBody([
                            html.P("システム内のユーザーを管理します。"),
                            dbc.Button(
                                "ユーザー一覧", color="primary",
                                className="me-2", id="user-list-btn"
                            ),
                            dbc.Button(
                                "新規ユーザー作成", color="success", id="new-user-btn"
                            )
                        ])
                    ]), width=6),
                    dbc.Col(dbc.Card([
                        dbc.CardHeader("💾 データ管理"),
                        dbc.CardBody([
                            html.P("現在の学習データをバックアップします。"),
                            dbc.Button("JSONバックアップ", color="warning", id="backup-btn")
                        ])
                    ]), width=6)
                ], className="mb-4"),
                html.Div(id="admin-statistics")
            ])
        ])

    # 該当するパスがない場合はメインページへ
    return create_main_layout(user_info)

# --- 管理者向け統計情報コールバック ---
@app.callback(
    Output('admin-statistics', 'children'),
    Input('url', 'pathname')
)
def update_admin_statistics(pathname):
    """管理者ページの統計情報を更新"""
    if pathname != '/admin' or not ALL_DATA:
        return ""

    try:
        total_students = 0
        total_subjects = set()
        total_books = 0
        completed_books = 0

        for students in ALL_DATA.values():
            total_students += len(students)
            for student_data in students.values():
                if 'progress' in student_data:
                    total_subjects.update(student_data['progress'].keys())
                    for subject_data in student_data['progress'].values():
                        for level_data in subject_data.values():
                            total_books += len(level_data)
                            completed_books += sum(
                                1 for book in level_data.values() if book.get('達成済')
                            )

        return dbc.Card([
            dbc.CardHeader("📊 システム統計情報"),
            dbc.CardBody(dbc.Row([
                dbc.Col([html.H4(total_students, className="text-info"), html.P("総生徒数")], width=3),
                dbc.Col([
                    html.H4(len(total_subjects), className="text-success"), html.P("総科目数")
                ], width=3),
                dbc.Col([
                    html.H4(total_books, className="text-primary"), html.P("総参考書数")
                ], width=3),
                dbc.Col([
                    html.H4(completed_books, className="text-warning"), html.P("完了参考書数")
                ], width=3)
            ]))
        ])

    # 多くのエラーが発生する可能性があるため、汎用的なExceptionを捕捉し、
    # アプリケーション全体のクラッシュを防ぎます。
    except Exception as e:
        return dbc.Alert(f"統計情報の取得に失敗しました: {str(e)}", color="danger")

# --- コールバック登録 ---
register_auth_callbacks(app)
register_main_callbacks(app, ALL_DATA)
register_progress_callbacks(app, ALL_DATA)
register_student_callbacks(app, ALL_DATA)
# 'data'引数を渡すように修正
register_admin_callbacks(app, ALL_DATA)


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