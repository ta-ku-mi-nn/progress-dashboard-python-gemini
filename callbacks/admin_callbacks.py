# callbacks/admin_callbacks.py

import json
import datetime
import sqlite3
import os
import pandas as pd
from dash import Input, Output, State, html, dcc, no_update
import dash_bootstrap_components as dbc

# ユーザー管理用の関数をインポート
from auth.user_manager import load_users, add_user

# --- データベースパスの定義 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(os.path.dirname(BASE_DIR), 'progress.db')
# -----------------------------

def register_admin_callbacks(app):
    """
    管理者ページの機能に関連するコールバックを登録します。
    """

    # --- (toggle_user_list_modal, toggle_new_user_modal, create_new_user は変更なし) ---
    @app.callback(
        [Output('user-list-modal', 'is_open'), Output('user-list-table', 'children')],
        [Input('user-list-btn', 'n_clicks'), Input('close-user-list-modal', 'n_clicks')],
        [State('user-list-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_user_list_modal(n_clicks, close_clicks, is_open):
        if not n_clicks and not close_clicks:
            return is_open, no_update
        if is_open:
            return False, no_update
        users = load_users()
        if not users:
            table = dbc.Alert("登録されているユーザーがいません。", color="info")
        else:
            table_header = [html.Thead(html.Tr([html.Th("ユーザー名"), html.Th("役割"), html.Th("所属校舎")]))]
            table_body = [html.Tbody([html.Tr([html.Td(user['username']), html.Td(user['role']), html.Td(user.get('school', 'N/A'))]) for user in users])]
            table = dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True)
        return True, table

    @app.callback(
        Output('new-user-modal', 'is_open'),
        [Input('new-user-btn', 'n_clicks'), Input('close-new-user-modal', 'n_clicks')],
        [State('new-user-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_new_user_modal(n_clicks, close_clicks, is_open):
        if n_clicks or close_clicks:
            return not is_open
        return is_open

    @app.callback(
        Output('new-user-alert', 'children'),
        Input('create-user-button', 'n_clicks'),
        [State('new-username', 'value'), State('new-password', 'value'), State('new-user-role', 'value'), State('new-user-school', 'value')],
        prevent_initial_call=True
    )
    def create_new_user(n_clicks, username, password, role, school):
        if not all([username, password, role]):
            return dbc.Alert("ユーザー名、パスワード、役割は必須です。", color="warning")
        success, message = add_user(username, password, role, school)
        if success:
            return dbc.Alert(message, color="success")
        else:
            return dbc.Alert(message, color="danger")

    # --- ★★★ データバックアップ処理を修正 ★★★ ---
    @app.callback(
        Output('download-backup', 'data'),
        Input('backup-btn', 'n_clicks'),
        prevent_initial_call=True,
    )
    def download_backup(n_clicks):
        if not n_clicks:
            return no_update

        try:
            # データベースに接続
            conn = sqlite3.connect(DATABASE_FILE)
            
            # 各テーブルのデータをPandas DataFrameとして読み込む
            users_df = pd.read_sql_query("SELECT * FROM users", conn)
            students_df = pd.read_sql_query("SELECT * FROM students", conn)
            progress_df = pd.read_sql_query("SELECT * FROM progress", conn)
            homework_df = pd.read_sql_query("SELECT * FROM homework", conn)
            master_textbooks_df = pd.read_sql_query("SELECT * FROM master_textbooks", conn)
            
            conn.close()

            # セキュリティのため、ユーザーのパスワードハッシュはバックアップから除外
            if 'password' in users_df.columns:
                users_df = users_df.drop(columns=['password'])
            
            # バックアップデータ全体を構成
            backup_data = {
                "export_date": datetime.datetime.now().isoformat(),
                "users": users_df.to_dict(orient='records'),
                "students": students_df.to_dict(orient='records'),
                "progress": progress_df.to_dict(orient='records'),
                "homework": homework_df.to_dict(orient='records'),
                "master_textbooks": master_textbooks_df.to_dict(orient='records')
            }

            backup_content = json.dumps(backup_data, indent=2, ensure_ascii=False)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            return dict(content=backup_content, filename=f"dashboard_backup_{timestamp}.json")

        except Exception as e:
            print(f"バックアップ作成中にエラーが発生しました: {e}")
            # エラーが発生したことをユーザーに通知するアラートなどを返すことも可能
            return no_update