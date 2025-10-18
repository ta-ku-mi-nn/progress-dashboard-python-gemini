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

    # --- 報告・要望の送信 (変更なし) ---
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


    # --- 一覧の表示 (共通化 - 変更なし) ---
    @app.callback(
        [Output('bug-list-container', 'children'),
         Output('request-list-container', 'children')],
        [Input('report-tabs', 'active_tab'),
         Input('report-update-trigger', 'data')]
    )
    def update_report_list(active_tab, update_trigger):
        ctx = callback_context
        # Initial call is allowed if active_tab is set, or trigger is data update
        if not ctx.triggered_id and active_tab is None: raise PreventUpdate
        if not active_tab: raise PreventUpdate

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
                if status == '見送り': return "dark"
                return "secondary"

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

    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---
    # --- ★★★ コールバック分割による修正 v5 ★★★ ---
    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---

    # --- Helper Function (共通ロジック) ---
    def _handle_modal_toggle_logic(report_type, item_clicks, close_detail_clicks, cancel_admin_clicks, user_info):
        """モーダル開閉の共通ロジック"""
        ctx = callback_context
        triggered_prop_id_str = ctx.triggered_prop_ids.get('.')
        if not triggered_prop_id_str:
            raise PreventUpdate

        # トリガーIDの解析
        try:
            triggered_id_str = triggered_prop_id_str.split('.')[0]
            if triggered_id_str.startswith('{'):
                 triggered_id_dict = json.loads(triggered_id_str)
            else:
                 raise PreventUpdate # パターンマッチングIDのみを想定
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Error parsing triggered ID in helper: {e}")
            raise PreventUpdate

        trigger_type = triggered_id_dict.get('type')
        trigger_report_type = triggered_id_dict.get('report_type') # トリガー要素の report_type

        # このヘルパー関数が処理すべき report_type でないトリガーは無視
        if trigger_report_type != report_type:
            # print(f"Helper ignored trigger for {trigger_report_type} in {report_type} context.")
            raise PreventUpdate

        # --- モーダルを閉じる処理 ---
        if trigger_type in ['close-detail-modal', 'cancel-admin-modal']:
            trigger_value = ctx.triggered[0]['value'] if ctx.triggered else None
            if not trigger_value: raise PreventUpdate # 実際のクリックでのみ閉じる
            print(f"Helper closing modal for {report_type}")
            # is_open, title, body, is_open_admin, admin_details, editing_id, status, message
            return False, no_update, no_update, False, no_update, no_update, no_update, no_update

        # --- リスト項目クリック時の処理 ---
        if trigger_type == 'report-item':
            clicked_n_clicks = ctx.triggered[0]['value'] if ctx.triggered else None
            if not clicked_n_clicks:
                # n_clicksが0やNoneになった場合はモーダルを閉じる
                print(f"Helper closing modal due to n_clicks={clicked_n_clicks} for {report_type}")
                return False, no_update, no_update, False, no_update, no_update, no_update, no_update

            report_id = triggered_id_dict.get('index')
            print(f"Helper handling item click for report_id={report_id}, report_type={report_type}")

            # データを取得
            get_func = get_all_bug_reports if report_type == 'bug' else get_all_feature_requests
            reports = get_func()
            report = next((r for r in reports if r['id'] == report_id), None)

            if not report:
                print("Report not found in helper.")
                # エラーメッセージを詳細モーダルに表示
                return True, "エラー", dbc.Alert("報告が見つかりません。", color="danger"), False, no_update, no_update, no_update, no_update

            is_admin = user_info and user_info.get('role') == 'admin'

            # 役割に応じて開くモーダルを決定
            if is_admin:
                print("Helper opening admin modal")
                details = html.Div([
                    html.H5(report['title']),
                    html.Small(f"報告者: {report['reporter_username']} | 日時: {report['report_date']}"),
                    dbc.Card(dbc.CardBody(report['description']), className="mt-2 mb-3 bg-light")
                ])
                # is_open, title, body, is_open_admin, admin_details, editing_id, status, message
                return False, no_update, no_update, True, details, report_id, report['status'], report.get('resolution_message', '')
            else:
                print("Helper opening detail modal")
                body = [
                    html.P([html.Strong("報告者: "), report['reporter_username']]),
                    html.P([html.Strong("報告日時: "), report['report_date']]),
                    html.Hr(),
                    html.P(report['description'], style={'whiteSpace': 'pre-wrap'}),
                ]
                if report['status'] in ['対応済', '見送り'] and report.get('resolution_message'):
                    status_label = "対応内容" if report['status'] == '対応済' else "コメント"
                    body.extend([ html.Hr(), html.Strong(f"{status_label}:"), dbc.Card(dbc.CardBody(report['resolution_message']), className="mt-2 bg-light") ])
                # is_open, title, body, is_open_admin, admin_details, editing_id, status, message
                return True, report['title'], body, False, no_update, no_update, no_update, no_update

        # 予期せぬトリガー
        raise PreventUpdate

    # --- Callback for BUG reports ---
    @app.callback(
        Output({'type': 'detail-modal', 'report_type': 'bug'}, 'is_open'),
        Output({'type': 'detail-modal-title', 'report_type': 'bug'}, 'children'),
        Output({'type': 'detail-modal-body', 'report_type': 'bug'}, 'children'),
        Output({'type': 'admin-modal', 'report_type': 'bug'}, 'is_open'),
        Output({'type': 'admin-detail-display', 'report_type': 'bug'}, 'children'),
        Output({'type': 'editing-id-store', 'report_type': 'bug'}, 'data'),
        Output({'type': 'status-dropdown', 'report_type': 'bug'}, 'value'),
        Output({'type': 'resolution-message-input', 'report_type': 'bug'}, 'value'),
        # Inputs using ALL
        Input({'type': 'report-item', 'report_type': ALL, 'index': ALL}, 'n_clicks'),
        Input({'type': 'close-detail-modal', 'report_type': ALL}, 'n_clicks'),
        Input({'type': 'cancel-admin-modal', 'report_type': ALL}, 'n_clicks'),
        State('auth-store', 'data'),
        prevent_initial_call=True
    )
    def handle_bug_modal_toggle(item_clicks, close_detail_clicks, cancel_admin_clicks, user_info):
        return _handle_modal_toggle_logic('bug', item_clicks, close_detail_clicks, cancel_admin_clicks, user_info)


    # --- Callback for REQUEST reports ---
    @app.callback(
        Output({'type': 'detail-modal', 'report_type': 'request'}, 'is_open'),
        Output({'type': 'detail-modal-title', 'report_type': 'request'}, 'children'),
        Output({'type': 'detail-modal-body', 'report_type': 'request'}, 'children'),
        Output({'type': 'admin-modal', 'report_type': 'request'}, 'is_open'),
        Output({'type': 'admin-detail-display', 'report_type': 'request'}, 'children'),
        Output({'type': 'editing-id-store', 'report_type': 'request'}, 'data'),
        Output({'type': 'status-dropdown', 'report_type': 'request'}, 'value'),
        Output({'type': 'resolution-message-input', 'report_type': 'request'}, 'value'),
        # Inputs using ALL
        Input({'type': 'report-item', 'report_type': ALL, 'index': ALL}, 'n_clicks'),
        Input({'type': 'close-detail-modal', 'report_type': ALL}, 'n_clicks'),
        Input({'type': 'cancel-admin-modal', 'report_type': ALL}, 'n_clicks'),
        State('auth-store', 'data'),
        prevent_initial_call=True
    )
    def handle_request_modal_toggle(item_clicks, close_detail_clicks, cancel_admin_clicks, user_info):
        return _handle_modal_toggle_logic('request', item_clicks, close_detail_clicks, cancel_admin_clicks, user_info)

    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---
    # --- ★★★ コールバック分割 修正ここまで ★★★ ---
    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---

    # --- Callback 1: 管理者によるステータス更新 (変更なし) ---
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

    # --- Callback 2: 管理者によるステータス更新 (変更なし) ---
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
        # Ensure click value is valid (greater than 0, not None)
        if triggered_index == -1 or not ctx.triggered or ctx.triggered[0].get('value') is None or ctx.triggered[0]['value'] == 0:
            raise PreventUpdate
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