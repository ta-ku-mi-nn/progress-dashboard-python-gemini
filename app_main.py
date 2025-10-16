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
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import datetime # datetimeをインポート
import plotly.io as pio

# --- グラフ描画の安定化のため、デフォルトテンプレートを設定 ---
pio.templates.default = "plotly_white"

# --- プロジェクトのルートディレクトリをPythonのパスに追加 ---
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


# --- 設定と外部ファイルのインポート ---
from config.settings import APP_CONFIG
from config.styles import APP_INDEX_STRING, EXTERNAL_STYLESHEETS
from data.nested_json_processor import get_all_subjects, get_student_info_by_id, get_student_progress_by_id, get_all_homework_for_student
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
from data.nested_json_processor import get_student_count_by_school, get_textbook_count_by_subject, get_student_info_by_id
from charts.chart_generator import create_progress_stacked_bar_chart, create_subject_achievement_bar


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

# RenderのDiskマウントパス（/var/data）が存在すればそちらを使用
RENDER_DATA_DIR = "/var/data"
if os.path.exists(RENDER_DATA_DIR):
    # 本番環境（Render）用のパス
    DB_DIR = RENDER_DATA_DIR
else:
    # ローカル開発環境用のパス (プロジェクトのルートディレクトリを指す)
    # このファイルの2階層上がプロジェクトルート
    DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_FILE = os.path.join(DB_DIR, 'progress.db')

# --- メインレイアウト ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=True),
    dcc.Store(id='auth-store', storage_type='session'),
    dcc.Store(id='school-selection-store', storage_type='session'),
    dcc.Store(id='student-selection-store', storage_type='session'),
    dcc.Store(id='admin-update-trigger', storage_type='memory'),
    dcc.Store(id='toast-trigger', storage_type='memory'),
    dcc.Store(id='item-to-delete-store', storage_type='memory'),

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
    # ★★★ ここにバックアップ用のDownloadコンポーネントを移動 ★★★
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
            html.H2("🔧 管理者メニュー", className="mt-4 mb-4"),
            dcc.ConfirmDialog(id='delete-user-confirm', message='本当にこのユーザーを削除しますか？'),
            dcc.ConfirmDialog(id='delete-student-confirm', message='本当にこの生徒を削除しますか？'),
            dcc.ConfirmDialog(id='delete-textbook-confirm', message='本当にこの参考書を削除しますか？'),
            dcc.ConfirmDialog(id='delete-preset-confirm', message='本当にこのプリセットを削除しますか？'),
            dbc.ListGroup([
                dbc.ListGroupItem([
                    html.Div([
                        html.H5("👥 ユーザー管理", className="mb-1"),
                        html.P("ユーザーの追加・一覧・編集・削除を行います。", className="mb-1 small text-muted"),
                    ], className="d-flex w-100 justify-content-between"),
                    html.Div([
                        dbc.Button("ユーザー一覧", id="user-list-btn", className="me-2"),
                        dbc.Button("新規ユーザー作成", id="new-user-btn", color="success")
                    ])
                ]),
                dbc.ListGroupItem([
                    html.Div([
                        html.H5("🧑‍🎓 生徒管理", className="mb-1"),
                        html.P("生徒情報の登録、編集、削除を行います。", className="mb-1 small text-muted"),
                    ], className="d-flex w-100 justify-content-between"),
                    dbc.Button("生徒を編集", id="open-student-management-modal-btn", color="warning")
                ]),
                dbc.ListGroupItem([
                    html.Div([
                        html.H5("📚 参考書マスター管理", className="mb-1"),
                        html.P("学習計画で使用する参考書のマスターデータを管理します。", className="mb-1 small text-muted"),
                    ], className="d-flex w-100 justify-content-between"),
                    dbc.Button("マスターを編集", id="open-master-textbook-modal-btn", color="dark")
                ]),
                dbc.ListGroupItem([
                    html.Div([
                        html.H5("📦 一括登録設定", className="mb-1"),
                        html.P("学習計画の一括登録用プリセットを作成・編集します。", className="mb-1 small text-muted"),
                    ], className="d-flex w-100 justify-content-between"),
                    dbc.Button("プリセットを編集", id="open-bulk-preset-modal-btn", color="secondary")
                ]),
                dbc.ListGroupItem([
                    html.Div([
                        html.H5("📢 更新履歴の管理", className="mb-1"),
                        html.P("アプリケーションの更新履歴を追加します。", className="mb-1 small text-muted"),
                    ], className="d-flex w-100 justify-content-between"),
                    dbc.Button("更新履歴を追加", id="add-changelog-btn", color="info")
                ]),
                dbc.ListGroupItem([
                    html.Div([
                        html.H5("💾 データバックアップ", className="mb-1"),
                        html.P("データベースの全データをJSONファイルとしてダウンロードします。", className="mb-1 small text-muted"),
                    ], className="d-flex w-100 justify-content-between"),
                    dbc.Button("バックアップを実行", id="backup-btn", color="primary")
                ]),
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

# --- ブラウザ自動起動 ---
def open_browser():
    """開発用にブラウザを自動で開く"""
    time.sleep(2)
    webbrowser.open(f"http://{APP_CONFIG['server']['host']}:{APP_CONFIG['server']['port']}")


if __name__ == '__main__':
    # このブロックはローカルでの開発時にのみ実行される
    print(
        f"🚀 アプリケーションを開発モードで起動中... http://{APP_CONFIG['server']['host']}:{APP_CONFIG['server']['port']}"
    )
    app.run(
        debug=True, # ローカル実行時はデバッグモードを有効にする
        host=APP_CONFIG['server']['host'],
        port=APP_CONFIG['server']['port']
    )