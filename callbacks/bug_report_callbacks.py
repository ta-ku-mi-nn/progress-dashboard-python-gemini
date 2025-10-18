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
    # (変更なし)
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
        if not ctx.triggered_id: raise PreventUpdate
        if not user_info or not user_info.get('username'):
            alert_msg = "ログインしていません。"
            is_bug_tab = active_tab == 'tab-bug-report'
            bug_alert = (dbc.Alert(alert_msg, color="danger"), True) if is_bug_tab else (no_update, no_update)
            req_alert = (dbc.Alert(alert_msg, color="danger"), True) if not is_bug_tab else (no_update, no_update)
            return bug_alert[0], bug_alert[1], req_alert[0], req_alert[1], no_update, no_update, no_update, no_update, no_update, no_update

        reporter = user_info['username']
        is_bug_submit = ctx.triggered_id == 'submit-bug-btn'
        title, description, report_type = (bug_title, bug_desc, 'bug') if is_bug_submit else (req_title, req_desc, 'request')
        add_func = add_bug_report if report_type == 'bug' else add_feature_request

        if not title or not description:
            alert_msg = "件名と詳細を入力してください。"
            bug_alert = (dbc.Alert(alert_msg, color="warning"), True) if is_bug_submit else (no_update, no_update)
            req_alert = (dbc.Alert(alert_msg, color="warning"), True) if not is_bug_submit else (no_update, no_update)
            return bug_alert[0], bug_alert[1], req_alert[0], req_alert[1], no_update, no_update, no_update, no_update, no_update, no_update

        success, message = add_func(reporter, title, description)

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': f'{report_type}_report'}
            update_trigger = {'timestamp': datetime.now().isoformat(), 'type': report_type}
            bug_title_clear, bug_desc_clear = ("", "") if is_bug_submit else (no_update, no_update)
            req_title_clear, req_desc_clear = ("", "") if not is_bug_submit else (no_update, no_update)
            bug_alert = ("", False) if is_bug_submit else (no_update, no_update)
            req_alert = ("", False) if not is_bug_submit else (no_update, no_update)
            return bug_alert[0], bug_alert[1], req_alert[0], req_alert[1], bug_title_clear, bug_desc_clear, req_title_clear, req_desc_clear, toast_data, update_trigger
        else:
            alert_msg = f"エラー: {message}"
            bug_alert = (dbc.Alert(alert_msg, color="danger"), True) if is_bug_submit else (no_update, no_update)
            req_alert = (dbc.Alert(alert_msg, color="danger"), True) if not is_bug_submit else (no_update, no_update)
            return bug_alert[0], bug_alert[1], req_alert[0], req_alert[1], no_update, no_update, no_update, no_update, no_update, no_update


    # --- 一覧の表示 (共通化) ---
    # (変更なし)
    @app.callback(
        [Output('bug-list-container', 'children'),
         Output('request-list-container', 'children')],
        [Input('report-tabs', 'active_tab'),
         Input('report-update-trigger', 'data')]
    )
    def update_report_list(active_tab, update_trigger):
        # Allow initial call or trigger by update
        ctx = callback_context
        if not ctx.triggered_id and active_tab is None : raise PreventUpdate # Prevent if no active tab on initial load
        if not active_tab: raise PreventUpdate # Prevent if active_tab becomes None later

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
                    id={'type': 'report-item', 'report_type': report_type, 'index': r['id']},
                    action=True,
                    className="report-list-item",
                    n_clicks=0 # Initialize n_clicks
                ) for r in reports
            ]
            list_content = dbc.ListGroup(items, flush=True)

        if report_type == 'bug':
            return list_content, no_update
        else:
            return no_update, list_content


    # ★★★★★★★★★★★★★★★★★★★★
    # ★★★ 修正箇所 (v4) ★★★
    # ★★★★★★★★★★★★★★★★★★★★
    @app.callback(
        # Outputs using MATCH
        Output({'type': 'detail-modal', 'report_type': MATCH}, 'is_open'),
        Output({'type': 'detail-modal-title', 'report_type': MATCH}, 'children'),
        Output({'type': 'detail-modal-body', 'report_type': MATCH}, 'children'),
        Output({'type': 'admin-modal', 'report_type': MATCH}, 'is_open'),
        Output({'type': 'admin-detail-display', 'report_type': MATCH}, 'children'),
        Output({'type': 'editing-id-store', 'report_type': MATCH}, 'data'),
        Output({'type': 'status-dropdown', 'report_type': MATCH}, 'value'),
        Output({'type': 'resolution-message-input', 'report_type': MATCH}, 'value'),
        # Inputs using ALL
        Input({'type': 'report-item', 'report_type': ALL, 'index': ALL}, 'n_clicks'),
        Input({'type': 'close-detail-modal', 'report_type': ALL}, 'n_clicks'), # Back to ALL
        Input({'type': 'cancel-admin-modal', 'report_type': ALL}, 'n_clicks'), # Back to ALL
        # State
        State('auth-store', 'data'),
        prevent_initial_call=True
    )
    def handle_modal_toggle_v4(item_clicks, close_detail_clicks, cancel_admin_clicks, user_info):
        ctx = callback_context
        triggered_prop_id_str = ctx.triggered_prop_ids.get('.')
        if not triggered_prop_id_str:
            raise PreventUpdate

        # --- Identify MATCH context ---
        # The callback runs twice (once for MATCH='bug', once for MATCH='request')
        # We need to know which context this instance is running under.
        current_match_context_report_type = ctx.outputs_list[0][0]['id']['report_type']

        # --- Identify Trigger ---
        try:
            triggered_id_str = triggered_prop_id_str.split('.')[0]
            if triggered_id_str.startswith('{'):
                 triggered_id_dict = json.loads(triggered_id_str)
            else:
                 # Should not happen with pattern matching inputs
                 raise PreventUpdate
        except (json.JSONDecodeError, IndexError):
            raise PreventUpdate

        trigger_type = triggered_id_dict.get('type')
        # Get the report_type from the element that was actually clicked
        trigger_report_type = triggered_id_dict.get('report_type')

        print(f"Callback Context: {current_match_context_report_type}, Trigger Type: {trigger_type}, Trigger Report Type: {trigger_report_type}") # Debug

        # --- IMPORTANT: Filter Execution ---
        # Only proceed if the trigger's report_type matches the callback's MATCH context
        if trigger_report_type != current_match_context_report_type:
            # print(f"Preventing update for context {current_match_context_report_type} because trigger was {trigger_report_type}")
            raise PreventUpdate

        # --- Handle Trigger ---
        # --- Closing Modals ---
        if trigger_type in ['close-detail-modal', 'cancel-admin-modal']:
            # Get n_clicks value for the specific button that triggered
            trigger_value = ctx.triggered[0]['value'] if ctx.triggered else None
            if not trigger_value: # Only close if n_clicks > 0
                raise PreventUpdate
            print(f"Closing modal for {current_match_context_report_type}")
            # Close both potential modals for this context
            return False, no_update, no_update, False, no_update, no_update, no_update, no_update

        # --- Opening Modals (report-item click) ---
        if trigger_type == 'report-item':
            # Get n_clicks value
            clicked_n_clicks = ctx.triggered[0]['value'] if ctx.triggered else None
            if not clicked_n_clicks: # Only open if n_clicks > 0
                 # If n_clicks is 0 or None, we might want to ensure modals are closed
                 # or just prevent update if they weren't the direct trigger.
                 # Let's ensure closed state for safety on 0 clicks.
                 print(f"Item click value is {clicked_n_clicks}. Ensuring modals closed for {current_match_context_report_type}.")
                 return False, no_update, no_update, False, no_update, no_update, no_update, no_update


            report_id = triggered_id_dict.get('index')
            print(f"Handling item click for report_id={report_id}, report_type={current_match_context_report_type}")

            # Fetch data (using the confirmed current_match_context_report_type)
            get_func = get_all_bug_reports if current_match_context_report_type == 'bug' else get_all_feature_requests
            reports = get_func()
            report = next((r for r in reports if r['id'] == report_id), None)

            if not report:
                 print("Report not found.")
                 return True, "エラー", dbc.Alert("報告が見つかりません。", color="danger"), False, no_update, no_update, no_update, no_update

            is_admin = user_info and user_info.get('role') == 'admin'

            # Open the correct modal based on role
            if is_admin:
                print("Admin user - opening admin modal")
                details = html.Div([
                    html.H5(report['title']),
                    html.Small(f"報告者: {report['reporter_username']} | 日時: {report['report_date']}"),
                    dbc.Card(dbc.CardBody(report['description']), className="mt-2 mb-3 bg-light")
                ])
                # Close detail, Open admin, set admin details, set store data
                return False, no_update, no_update, True, details, report_id, report['status'], report.get('resolution_message', '')
            else:
                print("Non-admin user - opening detail modal")
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
                # Open detail, Close admin, set detail title/body, clear store data
                return True, report['title'], body, False, no_update, no_update, no_update, no_update

        # Fallback if trigger type wasn't handled
        raise PreventUpdate

    # ★★★★★★★★★★★★★★★★★★★★
    # ★★★ 修正箇所ここまで ★★★
    # ★★★★★★★★★★★★★★★★★★★★


    # --- Callback 1: 管理者によるステータス更新 (MATCHED Outputs: Alert, Modal) ---
    # (変更なし)
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
        if not n_clicks or not bug_id: raise PreventUpdate
        report_type = button_id['report_type']
        resolve_func = resolve_bug if report_type == 'bug' else resolve_request
        update_func = update_bug_status if report_type == 'bug' else update_request_status
        if status in ['対応済', '見送り']: success, msg = resolve_func(bug_id, message, status)
        elif status in ['未対応', '対応中']: success, msg = update_func(bug_id, status)
        else: success = False; msg = "無効なステータスです。"
        if success: return "", False, False
        else: return dbc.Alert(f"エラー: {msg}", color="danger"), True, True

    # --- Callback 2: 管理者によるステータス更新 (Non-MATCHED Outputs: Stores) ---
    # (変更なし)
    @app.callback(
        [Output('toast-trigger', 'data', allow_duplicate=True),
         Output('report-update-trigger', 'data', allow_duplicate=True)],
        Input({'type': 'save-status-btn', 'report_type': ALL}, 'n_clicks'),
        [State({'type': 'editing-id-store', 'report_type': ALL}, 'data'),
         State({'type': 'status-dropdown', 'report_type': ALL}, 'value'),
         State({'type': 'resolution-message-input', 'report_type': ALL}, 'value'),
         State({'type': 'save-status-btn', 'report_type': ALL}, 'id')],
        prevent_initial_call=True
    )
    def save_status_stores(n_clicks_list, bug_id_list, status_list, message_list, button_id_list):
        ctx = callback_context
        triggered_prop_id_str = ctx.triggered_prop_ids.get('.')
        if not triggered_prop_id_str: raise PreventUpdate
        try:
            triggered_id_str = triggered_prop_id_str.split('.')[0]
            if triggered_id_str.startswith('{'): triggered_button_id = json.loads(triggered_id_str)
            else: raise PreventUpdate
        except (json.JSONDecodeError, IndexError) as e: raise PreventUpdate
        triggered_index = -1
        for i, btn_id in enumerate(button_id_list):
            if btn_id == triggered_button_id: triggered_index = i; break
        if triggered_index == -1 or not ctx.triggered or ctx.triggered[0].get('value') is None: raise PreventUpdate
        bug_id = bug_id_list[triggered_index]
        status = status_list[triggered_index]
        message = message_list[triggered_index]
        button_id = triggered_button_id
        if not bug_id: raise PreventUpdate
        report_type = button_id['report_type']
        resolve_func = resolve_bug if report_type == 'bug' else resolve_request
        update_func = update_bug_status if report_type == 'bug' else update_request_status
        if status in ['対応済', '見送り']: success, msg = resolve_func(bug_id, message, status)
        elif status in ['未対応', '対応中']: success, msg = update_func(bug_id, status)
        else: success = False; msg = "無効なステータスです。"
        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': msg, 'source': f'{report_type}_report'}
            update_trigger = {'timestamp': datetime.now().isoformat(), 'type': report_type}
            return toast_data, update_trigger
        else: return no_update, no_update