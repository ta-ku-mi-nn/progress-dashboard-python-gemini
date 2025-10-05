import json
import datetime
from dash import Input, Output, State, html, dcc, no_update
import dash_bootstrap_components as dbc

# ユーザー管理用の関数をインポート
from auth.user_manager import load_users, add_user

def register_admin_callbacks(app, data):
    """
    管理者ページの機能に関連するコールバックを登録します。

    Args:
        app (dash.Dash): Dashアプリケーションインスタンス。
        data (dict): アプリケーション起動時に読み込まれた全データ。
    """

    # --- ユーザー一覧モーダルの表示 ---
    @app.callback(
        [Output('user-list-modal', 'is_open'),
         Output('user-list-table', 'children')],
        [Input('user-list-btn', 'n_clicks'),
         Input('close-user-list-modal', 'n_clicks')],
        [State('user-list-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_user_list_modal(n_clicks, close_clicks, is_open):
        if not n_clicks and not close_clicks:
            return is_open, no_update

        if is_open: # 閉じるボタンが押された場合
            return False, no_update

        # データベースから直接ユーザーリストを読み込む
        users = load_users() 
        if not users:
            table = dbc.Alert("登録されているユーザーがいません。", color="info")
        else:
            table_header = [html.Thead(html.Tr([
                html.Th("ユーザー名"), html.Th("役割"), html.Th("所属校舎")
            ]))]
            table_body = [html.Tbody([
                html.Tr([
                    html.Td(user['username']),
                    html.Td(user['role']),
                    html.Td(user.get('school', 'N/A'))
                ]) for user in users
            ])]
            table = dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True)

        return True, table

    # --- 新規ユーザー作成モーダルの表示 ---
    @app.callback(
        Output('new-user-modal', 'is_open'),
        [Input('new-user-btn', 'n_clicks'),
         Input('close-new-user-modal', 'n_clicks')],
        [State('new-user-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_new_user_modal(n_clicks, close_clicks, is_open):
        if n_clicks or close_clicks:
            return not is_open
        return is_open

    # --- 新規ユーザー作成処理 ---
    @app.callback(
        Output('new-user-alert', 'children'),
        Input('create-user-button', 'n_clicks'),
        [State('new-username', 'value'),
         State('new-password', 'value'),
         State('new-user-role', 'value'),
         State('new-user-school', 'value')],
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

    # --- データバックアップ処理 ---
    @app.callback(
        Output('download-backup', 'data'),
        Input('backup-btn', 'n_clicks'),
        prevent_initial_call=True,
    )
    def download_backup(n_clicks):
        if n_clicks:
            # メモリ上の現在のデータからバックアップを作成
            full_data_structure = {"metadata": {}, "data": data}
            backup_content = json.dumps(full_data_structure, indent=2, ensure_ascii=False)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            return dict(content=backup_content, filename=f"backup_{timestamp}.json")
        return no_update