# callbacks/main_callbacks.py

import sqlite3
import os
import pandas as pd
from dash import Input, Output, State, dcc, html, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from data.nested_json_processor import get_subjects_for_student
# ★★★ インポートを追加 ★★★
from callbacks.progress_callbacks import create_welcome_layout, generate_dashboard_content

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

def register_main_callbacks(app):
    """メインページとグローバルセレクターに関連するコールバックを登録します。"""

    @app.callback(
        Output('student-dropdown-container', 'children'),
        Input('url', 'pathname'),
        State('auth-store', 'data'),
        State('student-selection-store', 'data')
    )
    def update_student_dropdown(pathname, user_info, selected_student_id):
        """
        ログインユーザーの校舎に所属する生徒のドロップダウンを生成・表示制御する。
        """
        if not user_info or pathname not in ['/', '/homework', '/past-exam']:
            return None

        user_school = user_info.get('school')
        if not user_school:
            return dbc.Alert("ユーザーに校舎が設定されていません。", color="danger")

        conn = sqlite3.connect(DATABASE_FILE)
        students_df = pd.read_sql_query(
            "SELECT id, name FROM students WHERE school = ?", conn, params=(user_school,)
        )
        conn.close()

        if students_df.empty:
            return dbc.Alert("この校舎には生徒が登録されていません。", color="info")

        return dcc.Dropdown(
            id='student-dropdown',
            options=[{'label': row['name'], 'value': row['id']} for _, row in students_df.iterrows()],
            placeholder="生徒を選択...",
            value=selected_student_id
        )

    # --- ★★★ ここから修正 ★★★ ---
    @app.callback(
        [Output('subject-tabs-container', 'children'),
        Output('dashboard-actions-container', 'children'),
        # ↓ Outputから 'dashboard-content-container' を削除
        ],
        Input('student-selection-store', 'data'),
        State('url', 'pathname')
    )
    def update_dashboard_on_student_select(student_id, pathname):
        """生徒が選択されたら、タブとアクションボタンを生成する（コンテンツは生成しない）"""
        if not student_id or pathname != '/':
            # 生徒が選択されていない場合は何も表示しない
            return None, None

        # --- 生徒選択時の処理 ---
        subjects = get_subjects_for_student(student_id)
        
        all_tabs = [dbc.Tab(label="総合", tab_id="総合")]
        if subjects:
            all_tabs.extend([dbc.Tab(label=subject, tab_id=subject) for subject in subjects])

        tabs = dbc.Tabs(all_tabs, id="subject-tabs", active_tab="総合")
        
        actions = dbc.ButtonGroup([
            dbc.Button("進捗を更新", id="bulk-register-btn", color="primary", outline=True),
            dbc.Button("レポート印刷", id="print-report-btn", color="info", outline=True, className="ms-2")
        ])

        # ↓ コンテンツは返さない
        return tabs, actions
    # --- ★★★ ここまで修正 ★★★ ---

    @app.callback(
        Output('student-selection-store', 'data'),
        Input('student-dropdown', 'value'),
        prevent_initial_call=True
    )
    def store_student_selection(student_id):
        """選択された生徒IDをセッションに保存する"""
        if student_id is None:
            raise PreventUpdate
        return student_id