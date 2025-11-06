# callbacks/auth_callbacks.py

import dash
from dash import Input, Output, State, no_update, html, callback_context
import dash_bootstrap_components as dbc

from auth.user_manager import authenticate_user, update_password
from data.nested_json_processor import get_students_for_instructor

def register_auth_callbacks(app):
    """認証関連のコールバックを登録します。"""

    # --- ログイン処理 ---
    @app.callback(
        Output('url', 'pathname'),
        Output('auth-store', 'data'),
        Output('login-alert', 'children'),
        Output('login-alert', 'is_open'), # 変更箇所: is_openをOutputに追加
        Input('login-button', 'n_clicks'),
        State('username-input', 'value'),
        State('password-input', 'value'),
        prevent_initial_call=True
    )
    def handle_login(n_clicks, username, password):
        if not n_clicks:
            return no_update, no_update, "", False

        if not username or not password:
            alert_msg = dbc.Alert("ユーザー名とパスワードを入力してください。", color="warning")
            return no_update, no_update, alert_msg, True

        user = authenticate_user(username, password)
        if user:
            user_data_for_store = {k: v for k, v in user.items() if k != 'password'}
            return '/', user_data_for_store, "", False
        else:
            alert_msg = dbc.Alert("ユーザー名またはパスワードが正しくありません。", color="danger")
            return no_update, no_update, alert_msg, True

    # --- ログアウト処理 (★修正箇所) ---
    @app.callback(
        # Output('url', 'pathname', allow_duplicate=True), # <-- ★ 削除
        Output('auth-store', 'clear_data'),
        Input('logout-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_logout(n_clicks):
        if n_clicks:
            # return '/login', True # <-- ★ 変更
            return True # ★ セッションストレージをクリアするだけ
        # return no_update, no_update # <-- ★ 変更
        return no_update


    # --- プロフィール関連のコールバック ---
    @app.callback(
        Output('user-profile-modal', 'is_open'),
        [Input('user-profile-btn', 'n_clicks'),
         Input('close-profile-modal', 'n_clicks')],
        [State('user-profile-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_user_profile_modal(n_clicks, close_clicks, is_open):
        ctx = callback_context

        if ctx.triggered and ctx.triggered[0]['value'] is not None:
            return not is_open

        return is_open

    @app.callback(
        [Output('profile-username', 'children'),
         Output('profile-role', 'children'),
         Output('profile-school', 'children'),
         Output('profile-assigned-students', 'children')],
        Input('user-profile-modal', 'is_open'),
        State('auth-store', 'data')
    )
    def display_user_profile(is_open, user_data):
        if is_open and user_data:
            user_id = user_data.get('id')
            assigned_students = get_students_for_instructor(user_id)

            if not assigned_students:
                student_list_component = html.P("担当生徒はいません。", className="text-muted")
            else:
                student_list_component = dbc.ListGroup(
                    [dbc.ListGroupItem(s) for s in assigned_students],
                    flush=True,
                    style={'maxHeight': '150px', 'overflowY': 'auto'}
                )

            return (
                user_data.get('username', 'N/A'),
                user_data.get('role', 'N/A'),
                user_data.get('school', 'N/A'),
                student_list_component
            )
        return no_update, no_update, no_update, no_update

    @app.callback(
        Output('password-change-modal', 'is_open'),
        [Input('change-password-button', 'n_clicks'),
         Input('close-password-modal', 'n_clicks')],
        [State('password-change-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_password_change_modal(n_clicks, close_clicks, is_open):
        ctx = callback_context
        if ctx.triggered and ctx.triggered[0]['value'] is not None:
            return not is_open
        return is_open

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
        if not n_clicks:
            return no_update

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