# callbacks/bug_report_callbacks.py

from dash import Input, Output, State, html, no_update, callback_context, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime
import json # jsonをインポート

from data.nested_json_processor import (
    add_bug_report, get_all_bug_reports, update_bug_status, resolve_bug,
    add_feature_request, get_all_feature_requests, update_request_status, resolve_request # 要望用の関数をインポート
)

def register_bug_report_callbacks(app):
    """不具合報告・要望ページのコールバックを登録する"""

    # --- 報告・要望の送信 ---
    @app.callback(
        [Output('bug-alert', 'children'), Output('bug-alert', 'is_open'),
         Output('request-alert', 'children'), Output('request-alert', 'is_open'),
         Output('bug-title', 'value'), Output('bug-description', 'value'),
         Output('request-title', 'value'), Output('request-description', 'value'),
         Output('toast-trigger', 'data', allow_duplicate=True),
         Output('report-update-trigger', 'data')], # リスト更新トリガー
        [Input('submit-bug-btn', 'n_clicks'), Input('submit-request-btn', 'n_clicks')],
        [State('report-tabs', 'active_tab'), # アクティブなタブを取得
         State('auth-store', 'data'),
         State('bug-title', 'value'), State('bug-description', 'value'),
         State('request-title', 'value'), State('request-description', 'value')],
        prevent_initial_call=True
    )
    def submit_report_or_request(bug_clicks, request_clicks, active_tab, user_info,
                                 bug_title, bug_desc, req_title, req_desc):
        ctx = callback_context
        if not ctx.triggered_id:
            raise PreventUpdate

        if not user_info or not user_info.get('username'):
            alert = dbc.Alert("ログインしていません。", color="danger")
            if active_tab == 'tab-bug-report':
                return alert, True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            else:
                return no_update, no_update, alert, True, no_update, no_update, no_update, no_update, no_update, no_update

        reporter = user_info['username']
        # triggered_id を直接比較
        title, description, report_type = (bug_title, bug_desc, 'bug') if ctx.triggered_id == 'submit-bug-btn' else (req_title, req_desc, 'request')
        add_func = add_bug_report if report_type == 'bug' else add_feature_request

        if not title or not description:
            alert = dbc.Alert("件名と詳細を入力してください。", color="warning")
            if report_type == 'bug':
                return alert, True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            else:
                return no_update, no_update, alert, True, no_update, no_update, no_update, no_update, no_update, no_update

        success, message = add_func(reporter, title, description)

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': f'{report_type}_report'}
            update_trigger = {'timestamp': datetime.now().isoformat(), 'type': report_type}
            if report_type == 'bug':
                return "", False, no_update, no_update, "", "", no_update, no_update, toast_data, update_trigger
            else:
                return no_update, no_update, "", False, no_update, no_update, "", "", toast_data, update_trigger
        else:
            alert = dbc.Alert(f"エラー: {message}", color="danger")
            if report_type == 'bug':
                return alert, True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            else:
                return no_update, no_update, alert, True, no_update, no_update, no_update, no_update, no_update, no_update

    # --- 一覧の表示 (共通化) ---
    @app.callback(
        [Output('bug-list-container', 'children'),
         Output('request-list-container', 'children')],
        [Input('report-tabs', 'active_tab'), # urlから変更
         Input('report-update-trigger', 'data')] # 更新トリガー
    )
    def update_report_list(active_tab, update_trigger):
        if not active_tab:
            raise PreventUpdate

        report_type = 'bug' if active_tab == 'tab-bug-report' else 'request'
        get_func = get_all_bug_reports if report_type == 'bug' else get_all_feature_requests
        no_report_message = "報告されている不具合はありません。" if report_type == 'bug' else "登録されている要望はありません。"

        reports = get_func()
        if not reports:
            list_content = dbc.Alert(no_report_message, color="info")
        else:
            def get_status_color(status):
                if status == '対応済': return "success"
                if status == '対応中': return "warning"
                if status == '見送り': return "dark" # 要望用
                return "secondary" # 未対応

            items = [
                dbc.ListGroupItem(
                    dbc.Row([
                        dbc.Col(f"[{r['report_date']}] {r['title']}", width=8),
                        dbc.Col(r['reporter_username'], width=2),
                        dbc.Col(dbc.Badge(r['status'], color=get_status_color(r['status'])), width=2),
                    ], align="center"),
                    # report_type を含める
                    id={'type': 'report-item', 'report_type': report_type, 'index': r['id']},
                    action=True,
                    className="report-list-item"
                ) for r in reports
            ]
            list_content = dbc.ListGroup(items, flush=True)

        if report_type == 'bug':
            return list_content, no_update
        else:
            return no_update, list_content

    @app.callback(
        # --- Outputs for BOTH modal types ---
        Output({'type': 'detail-modal', 'report_type': MATCH}, 'is_open'),
        Output({'type': 'detail-modal-title', 'report_type': MATCH}, 'children'),
        Output({'type': 'detail-modal-body', 'report_type': MATCH}, 'children'),
        Output({'type': 'admin-modal', 'report_type': MATCH}, 'is_open'),
        Output({'type': 'editing-id-store', 'report_type': MATCH}, 'data'),
        Output({'type': 'status-dropdown', 'report_type': MATCH}, 'value'),
        Output({'type': 'resolution-message-input', 'report_type': MATCH}, 'value'),
        Output({'type': 'admin-detail-display', 'report_type': MATCH}, 'children'),
        # --- Inputs ---
        [Input({'type': 'report-item', 'report_type': MATCH, 'index': ALL}, 'n_clicks'),
        Input({'type': 'close-detail-modal', 'report_type': MATCH}, 'n_clicks'),
        Input({'type': 'cancel-admin-modal', 'report_type': MATCH}, 'n_clicks')],
        # --- States ---
        [State('auth-store', 'data'),
        State({'type': 'report-item', 'report_type': MATCH, 'index': ALL}, 'id'),
        # Stateを追加: モーダルが開いているかどうかの状態も確認する
        State({'type': 'detail-modal', 'report_type': MATCH}, 'is_open'),
        State({'type': 'admin-modal', 'report_type': MATCH}, 'is_open'),
        ],
        prevent_initial_call=True
    )
    def handle_modal_toggle(item_clicks, close_detail_clicks, cancel_admin_clicks,
                            user_info, item_ids, detail_is_open, admin_is_open): # Stateの引数を追加
        ctx = callback_context
        triggered_input_id = ctx.triggered_id

        # --- デバッグ出力 ---
        print(f"\n--- handle_modal_toggle triggered ---")
        print(f"Triggered ID: {triggered_input_id}")
        print(f"User Info Role: {user_info.get('role') if user_info else 'No User Info'}")
        print(f"Item Clicks: {item_clicks}")
        print(f"Close Detail Clicks: {close_detail_clicks}")
        print(f"Cancel Admin Clicks: {cancel_admin_clicks}")
        print(f"Detail Modal Open State: {detail_is_open}")
        print(f"Admin Modal Open State: {admin_is_open}")
        # --- デバッグ出力ここまで ---

        # トリガーがない場合は更新しない
        if not triggered_input_id:
            print("No triggered ID, preventing update.")
            raise PreventUpdate

        # triggered_idが辞書でない場合（close/cancelボタン）はそのまま使う
        # 辞書の場合（report-item）は、それをそのまま使う
        trigger_info = triggered_input_id
        report_type = trigger_info.get('report_type') if isinstance(trigger_info, dict) else None
        trigger_type = trigger_info.get('type') if isinstance(trigger_info, dict) else None # typeを取得

        print(f"Extracted report_type: {report_type}")
        print(f"Extracted trigger_type: {trigger_type}")

        is_admin = user_info and user_info.get('role') == 'admin'

        # --- モーダルを閉じる処理 ---
        # detail-modal または admin-modal の閉じる/キャンセルボタンが押された場合
        if trigger_type in ['close-detail-modal', 'cancel-admin-modal']:
            print(f"Closing modal: {trigger_type}")
            # is_open を False にして返す
            # Detail Modal Outputs , Admin Modal Outputs
            return False, no_update, no_update, False, no_update, no_update, no_update, no_update

        # --- リスト項目クリック時の処理 ---
        if trigger_type == 'report-item':
            print("Report item clicked.")
            # クリックされたn_clicksを取得 (単一の値のはず)
            clicked_n_clicks = None
            # ctx.triggered は [{ 'prop_id': '...', 'value': n_clicks }, ...] のリスト
            if ctx.triggered and ctx.triggered[0].get('value') is not None:
                clicked_n_clicks = ctx.triggered[0]['value']
            print(f"Clicked n_clicks value: {clicked_n_clicks}")

            # n_clicks が 0 または None の場合はモーダルを開かない (既に開いているモーダルも閉じる)
            if not clicked_n_clicks:
                print("Click value is None or 0, closing modals or preventing update.")
                # Detail Modal Outputs , Admin Modal Outputs
                return False, no_update, no_update, False, no_update, no_update, no_update, no_update


            report_id = trigger_info['index']
            print(f"Target report_id: {report_id}")
            get_func = get_all_bug_reports if report_type == 'bug' else get_all_feature_requests
            reports = get_func()
            report = next((r for r in reports if r['id'] == report_id), None)

            if not report:
                print("Report not found.")
                # エラー処理（どちらのモーダルも開かない）
                return False, "エラー", "報告が見つかりません。", False, None, no_update, no_update, None

            # --- ユーザーの役割に応じて開くモーダルを決定 ---
            if is_admin:
                print("User is admin, preparing admin modal.")
                # 管理者モーダルを開く準備
                details = html.Div([
                    html.H5(report['title']),
                    html.Small(f"報告者: {report['reporter_username']} | 日時: {report['report_date']}"),
                    dbc.Card(dbc.CardBody(report['description']), className="mt-2 mb-3 bg-light")
                ])
                # Detail Modal Outputs , Admin Modal Outputs
                return False, no_update, no_update, True, report_id, report['status'], report.get('resolution_message', ''), details
            else:
                print("User is not admin, preparing detail modal.")
                # 詳細モーダルを開く準備
                body = [
                    html.P([html.Strong("報告者: "), report['reporter_username']]),
                    html.P([html.Strong("報告日時: "), report['report_date']]),
                    html.Hr(),
                    html.P(report['description'], style={'whiteSpace': 'pre-wrap'}),
                ]
                if report['status'] in ['対応済', '見送り'] and report.get('resolution_message'):
                    status_label = "対応内容" if report['status'] == '対応済' else "コメント"
                    body.extend([
                        html.Hr(),
                        html.Strong(f"{status_label}:"),
                        dbc.Card(dbc.CardBody(report['resolution_message']), className="mt-2 bg-light")
                    ])
                # Detail Modal Outputs , Admin Modal Outputs
                return True, report['title'], body, False, no_update, no_update, no_update, no_update

        # 上記のいずれにも該当しない場合（予期せぬトリガーなど）は更新しない
        print("Trigger type not matched, preventing update.")
        raise PreventUpdate # または return [no_update] * 8 でも可

    # --- Callback 1: 管理者によるステータス更新 (MATCHED Outputs: Alert, Modal) ---
    @app.callback(
        [Output({'type': 'admin-alert', 'report_type': MATCH}, 'children'),
         Output({'type': 'admin-alert', 'report_type': MATCH}, 'is_open'),
         Output({'type': 'admin-modal', 'report_type': MATCH}, 'is_open', allow_duplicate=True)],
        Input({'type': 'save-status-btn', 'report_type': MATCH}, 'n_clicks'),
        [State({'type': 'editing-id-store', 'report_type': MATCH}, 'data'),
         State({'type': 'status-dropdown', 'report_type': MATCH}, 'value'),
         State({'type': 'resolution-message-input', 'report_type': MATCH}, 'value'),
         State({'type': 'save-status-btn', 'report_type': MATCH}, 'id')],
        prevent_initial_call=True
    )
    def save_status_matched(n_clicks, bug_id, status, message, button_id):
        if not n_clicks or not bug_id:
            raise PreventUpdate

        report_type = button_id['report_type']
        resolve_func = resolve_bug if report_type == 'bug' else resolve_request
        update_func = update_bug_status if report_type == 'bug' else update_request_status

        if status in ['対応済', '見送り']:
            success, msg = resolve_func(bug_id, message, status)
        elif status in ['未対応', '対応中']:
            success, msg = update_func(bug_id, status)
        else:
            success = False
            msg = "無効なステータスです。"

        if success:
            # アラートクリア、モーダル閉じる
            return "", False, False
        else:
            # エラーアラート表示、モーダル開いたまま
            return dbc.Alert(f"エラー: {msg}", color="danger"), True, True

    # --- Callback 2: 管理者によるステータス更新 (Non-MATCHED Outputs: Stores) ---
    @app.callback(
        [Output('toast-trigger', 'data', allow_duplicate=True),
         Output('report-update-trigger', 'data', allow_duplicate=True)],
        Input({'type': 'save-status-btn', 'report_type': ALL}, 'n_clicks'), # Use ALL here
        [State({'type': 'editing-id-store', 'report_type': ALL}, 'data'),
         State({'type': 'status-dropdown', 'report_type': ALL}, 'value'),
         State({'type': 'resolution-message-input', 'report_type': ALL}, 'value'),
         State({'type': 'save-status-btn', 'report_type': ALL}, 'id')], # Get ALL IDs
        prevent_initial_call=True
    )
    def save_status_stores(n_clicks_list, bug_id_list, status_list, message_list, button_id_list):
        ctx = callback_context
        # Find which button was actually clicked
        triggered_button_id_str = ctx.triggered_id
        if not triggered_button_id_str:
            raise PreventUpdate

        # Parse the triggered ID string back into a dictionary
        try:
            triggered_button_id = json.loads(triggered_button_id_str)
        except json.JSONDecodeError:
            raise PreventUpdate # Should not happen if IDs are correct

        # Find the index corresponding to the triggered button
        triggered_index = -1
        for i, btn_id in enumerate(button_id_list):
            if btn_id == triggered_button_id:
                triggered_index = i
                break

        if triggered_index == -1 or n_clicks_list[triggered_index] is None:
            raise PreventUpdate # Click not found or n_clicks is None

        # Get the corresponding states using the found index
        bug_id = bug_id_list[triggered_index]
        status = status_list[triggered_index]
        message = message_list[triggered_index]
        button_id = triggered_button_id # Already have the dict

        if not bug_id: # Check if bug_id is valid
            raise PreventUpdate

        report_type = button_id['report_type']
        resolve_func = resolve_bug if report_type == 'bug' else resolve_request
        update_func = update_bug_status if report_type == 'bug' else update_request_status

        if status in ['対応済', '見送り']:
            success, msg = resolve_func(bug_id, message, status)
        elif status in ['未対応', '対応中']:
             success, msg = update_func(bug_id, status)
        else:
            success = False
            msg = "無効なステータスです。" # Should ideally not happen due to dropdown

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': msg, 'source': f'{report_type}_report'}
            update_trigger = {'timestamp': datetime.now().isoformat(), 'type': report_type}
            # トースト表示、リスト更新トリガー
            return toast_data, update_trigger
        else:
            # 失敗時は何もしない (アラートは別コールバックで表示)
            return no_update, no_update

    # --- IDを汎用化するためのヘルパー ---
    # (不要になったため削除)