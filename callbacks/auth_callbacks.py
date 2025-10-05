"""
認証（ログイン、ログアウト、プロファイル管理）に関連するコールバックを定義します。
"""
import dash
from dash import Input, Output, State, no_update
import dash_bootstrap_components as dbc

# ユーザー認証とパスワード更新の関数を user_manager からインポート
from auth.user_manager import authenticate_user, update_password

def register_auth_callbacks(app):
    """
    認証関連のコールバックを登録します。

    Args:
        app (dash.Dash): Dashアプリケーションインスタンス。
    """

    # --- ログイン処理 ---
    @app.callback(
        [Output('url', 'pathname'),
         Output('auth-store', 'data'),
         Output('login-alert', 'children')],
        Input('login-button', 'n_clicks'),
        [State('username-input', 'value'),
         State('password-input', 'value')],
        prevent_initial_call=True
    )
    def handle_login(n_clicks, username, password):
        if not n_clicks:
            return no_update, no_update, ""

        if not username or not password:
            return no_update, no_update, dbc.Alert("ユーザー名とパスワードを入力してください。", color="warning")

        user = authenticate_user(username, password)
        if user:
            # パスワードハッシュはセッションに保存しない
            user_data_for_store = {k: v for k, v in user.items() if k != 'password'}
            return '/', user_data_for_store, ""  # ログイン成功後、メインページにリダイレクト
        else:
            return no_update, no_update, dbc.Alert("ユーザー名またはパスワードが正しくありません。", color="danger")

    # --- ログアウト処理 ---
    @app.callback(
        Output('url', 'pathname', allow_duplicate=True),
        Input('logout-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_logout(n_clicks):
        if n_clicks:
            # ログインページにリダイレクトすることで、display_pageコールバックが
            # dcc.Storeを空にし、事実上のログアウトとなる
            return '/login'
        return no_update

    # --- ユーザープロファイルモーダルの表示 ---
    @app.callback(
        Output('user-profile-modal', 'is_open'),
        [Input('user-menu', 'n_clicks'),
         Input('close-profile-modal', 'n_clicks')],
        [State('user-profile-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_user_profile_modal(n_clicks, close_clicks, is_open):
        if n_clicks or close_clicks:
            return not is_open
        return is_open

    # --- プロファイルモーダルにユーザー情報を表示 ---
    @app.callback(
        [Output('profile-username', 'children'),
         Output('profile-role', 'children'),
         Output('profile-school', 'children')],
        Input('user-profile-modal', 'is_open'),
        State('auth-store', 'data')
    )
    def display_user_profile(is_open, user_data):
        if is_open and user_data:
            return (
                user_data.get('username', 'N/A'),
                user_data.get('role', 'N/A'),
                user_data.get('school', 'N/A')
            )
        return no_update, no_update, no_update

    # --- パスワード変更モーダルの表示 ---
    @app.callback(
        Output('password-change-modal', 'is_open'),
        [Input('change-password-button', 'n_clicks'),
         Input('close-password-modal', 'n_clicks')],
        [State('password-change-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_password_change_modal(n_clicks, close_clicks, is_open):
        if n_clicks or close_clicks:
            return not is_open
        return is_open

    # --- パスワード変更処理 ---
    @app.callback(
        Output('password-change-alert', 'children'),
        Input('confirm-password-change', 'n_clicks'),
        [State('current-password', 'value'),
         State('new-password', 'value'),
         State('confirm-new-password', 'value'),
         State('auth-store', 'data')],
        prevent_initial_call=True
    )
    def handle_password_change(n_clicks, current_pass, new_pass, confirm_pass, user_data):
        if not user_data:
            return dbc.Alert("セッションが切れました。再度ログインしてください。", color="danger")

        username = user_data.get('username')
        user = authenticate_user(username, current_pass)

        if not user:
            return dbc.Alert("現在のパスワードが正しくありません。", color="danger")
        
        if not new_pass or not confirm_pass:
            return dbc.Alert("新しいパスワードを入力してください。", color="warning")

        if new_pass != confirm_pass:
            return dbc.Alert("新しいパスワードが一致しません。", color="warning")

        success, message = update_password(username, new_pass)
        if success:
            return dbc.Alert("パスワードが正常に変更されました。", color="success")
        else:
            return dbc.Alert(f"エラー: {message}", color="danger")