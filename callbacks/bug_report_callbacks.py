# callbacks/bug_report_callbacks.py

from dash import Input, Output, State, html, no_update, callback_context, ALL, MATCH, clientside_callback
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime
import json

from data.nested_json_processor import (
    add_bug_report, get_all_bug_reports, update_bug_status, resolve_bug,
    add_feature_request, get_all_feature_requests, update_request_status, resolve_request
)

def register_bug_report_callbacks(app):
    """不具合報告・要望ページのコールバックを登録する"""

    # --- ↓↓↓ コールバックを2つに分割 ↓↓↓ ---

    # --- 報告 (Bug Report) の送信 ---
    @app.callback(
        [Output('bug-submit-alert', 'children'),
         Output('bug-submit-alert', 'is_open'),
         Output('bug-title', 'value'), # valueをクリアするためOutputに追加
         Output('bug-description', 'value'), # valueをクリアするためOutputに追加
         Output('toast-trigger', 'data', allow_duplicate=True),
         Output('report-update-trigger', 'data', allow_duplicate=True)],
        Input('submit-bug-btn', 'n_clicks'),
        [State('auth-store', 'data'),
         State('bug-title', 'value'),
         State('bug-description', 'value')],
        prevent_initial_call=True
    )
    def submit_bug_report(bug_clicks, user_info, bug_title, bug_desc):
        if not bug_clicks: raise PreventUpdate

        if not user_info or not user_info.get('username'):
            alert_msg = dbc.Alert("ログインしていません。", color="danger")
            # 出力をコールバック定義に合わせて調整
            return alert_msg, True, no_update, no_update, no_update, no_update

        reporter = user_info['username']
        title, description = bug_title, bug_desc

        if not title or not description:
            alert_msg = dbc.Alert("件名と詳細を入力してください。", color="warning")
            # 出力をコールバック定義に合わせて調整
            return alert_msg, True, no_update, no_update, no_update, no_update

        success, message = add_bug_report(reporter, title, description)

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'bug_report'}
            update_trigger = {'timestamp': datetime.now().isoformat(), 'type': 'bug'}
            # 成功したらフォームをクリアし、アラートを閉じる
            return "", False, "", "", toast_data, update_trigger
        else:
            alert_msg = dbc.Alert(f"エラー: {message}", color="danger")
            # 出力をコールバック定義に合わせて調整
            return alert_msg, True, no_update, no_update, no_update, no_update

    # --- 要望 (Feature Request) の送信 ---
    @app.callback(
        [Output('request-submit-alert', 'children'),
         Output('request-submit-alert', 'is_open'),
         Output('request-title', 'value'), # valueをクリアするためOutputに追加
         Output('request-description', 'value'), # valueをクリアするためOutputに追加
         Output('toast-trigger', 'data', allow_duplicate=True),
         Output('report-update-trigger', 'data', allow_duplicate=True)],
        Input('submit-request-btn', 'n_clicks'),
        [State('auth-store', 'data'),
         State('request-title', 'value'),
         State('request-description', 'value')],
        prevent_initial_call=True
    )
    def submit_feature_request(request_clicks, user_info, req_title, req_desc):
        if not request_clicks: raise PreventUpdate

        if not user_info or not user_info.get('username'):
            alert_msg = dbc.Alert("ログインしていません。", color="danger")
            # 出力をコールバック定義に合わせて調整
            return alert_msg, True, no_update, no_update, no_update, no_update

        reporter = user_info['username']
        title, description = req_title, req_desc

        if not title or not description:
            alert_msg = dbc.Alert("件名と詳細を入力してください。", color="warning")
            # 出力をコールバック定義に合わせて調整
            return alert_msg, True, no_update, no_update, no_update, no_update

        success, message = add_feature_request(reporter, title, description)

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'request_report'}
            update_trigger = {'timestamp': datetime.now().isoformat(), 'type': 'request'}
             # 成功したらフォームをクリアし、アラートを閉じる
            return "", False, "", "", toast_data, update_trigger
        else:
            alert_msg = dbc.Alert(f"エラー: {message}", color="danger")
             # 出力をコールバック定義に合わせて調整
            return alert_msg, True, no_update, no_update, no_update, no_update

    # --- ↑↑↑ コールバック分割ここまで ↑↑↑ ---


    # --- 一覧の表示 (変更なし) ---
    @app.callback(
        [Output('bug-list-container', 'children'), Output('request-list-container', 'children')],
        [Input('report-tabs', 'active_tab'), Input('report-update-trigger', 'data')]
    )
    def update_report_list(active_tab, update_trigger):
        # (内容は変更なし)
        ctx = callback_context
        if not ctx.triggered_id and active_tab is None: raise PreventUpdate
        if not active_tab: raise PreventUpdate # active_tabがNoneの場合の処理を追加
        report_type = 'bug' if active_tab == 'tab-bug-report' else 'request'
        get_func = get_all_bug_reports if report_type == 'bug' else get_all_feature_requests
        no_report_message = "報告されている不具合はありません。" if report_type == 'bug' else "登録されている要望はありません。"
        reports = get_func()
        if not reports: list_content = dbc.Alert(no_report_message, color="info")
        else:
            def get_status_color(status):
                if status == '対応済': return "success";
                if status == '対応中': return "warning";
                if status == '見送り': return "dark";
                return "secondary"
            items = [ dbc.ListGroupItem( dbc.Row([ dbc.Col(f"[{r['report_date']}] {r['title']}", width=8), dbc.Col(r['reporter_username'], width=2), dbc.Col(dbc.Badge(r['status'], color=get_status_color(r['status'])), width=2), ], align="center"), id={'type': 'report-item', 'report_type': report_type, 'index': r['id']}, action=True, className="report-list-item", n_clicks=0 ) for r in reports ]
            list_content = dbc.ListGroup(items, flush=True)

        # Ensure correct output based on report_type
        if report_type == 'bug':
            return list_content, no_update
        else: # report_type == 'request'
            return no_update, list_content


    # --- モーダル表示/非表示 (変更なし) ---
    @app.callback(
        # ... (Outputs) ...
        Output('bug-detail-modal', 'is_open'),
        Output('bug-detail-modal-title', 'children'),
        Output('bug-detail-modal-body', 'children'),
        Output('bug-admin-modal', 'is_open'),
        Output('bug-admin-detail-display', 'children'),
        Output('bug-status-dropdown', 'value'),
        Output('bug-resolution-message-input', 'value'),
        Output('request-detail-modal', 'is_open'),
        Output('request-detail-modal-title', 'children'),
        Output('request-detail-modal-body', 'children'),
        Output('request-admin-modal', 'is_open'),
        Output('request-admin-detail-display', 'children'),
        Output('request-status-dropdown', 'value'),
        Output('request-resolution-message-input', 'value'),
        Output('editing-report-store', 'data', allow_duplicate=True),
        # ... (Inputs and State) ...
        Input({'type': 'report-item', 'report_type': ALL, 'index': ALL}, 'n_clicks'),
        Input('close-bug-detail-modal', 'n_clicks'),
        Input('cancel-bug-admin-modal', 'n_clicks'),
        Input('close-request-detail-modal', 'n_clicks'),
        Input('cancel-request-admin-modal', 'n_clicks'),
        Input('report-modal-control-store', 'data'),
        State('auth-store', 'data'),
        prevent_initial_call=True
    )
    def handle_modal_toggle_final(item_clicks, close_bug_detail, cancel_bug_admin,
                                  close_req_detail, cancel_req_admin, control_data, user_info):
        # (内容は変更なし)
        ctx = callback_context
        triggered_prop_id_str = next(iter(ctx.triggered_prop_ids.keys()), None)
        if not triggered_prop_id_str: raise PreventUpdate

        bug_detail_open = no_update; bug_detail_title = no_update; bug_detail_body = no_update
        bug_admin_open = no_update; bug_admin_display = no_update; bug_status_val = no_update; bug_message_val = no_update
        req_detail_open = no_update; req_detail_title = no_update; req_detail_body = no_update
        req_admin_open = no_update; req_admin_display = no_update; req_status_val = no_update; req_message_val = no_update
        store_data_out = no_update

        trigger_value = None; triggered_id_dict = None; is_pattern_match = False
        try:
            id_str = triggered_prop_id_str.split('.')[0]
            if id_str.startswith('{'): triggered_id_dict = json.loads(id_str); is_pattern_match = True
            else: triggered_id_dict = {'type': id_str}
        except (json.JSONDecodeError, IndexError, AttributeError): raise PreventUpdate
        for trigger_info in ctx.triggered:
            if trigger_info['prop_id'] == triggered_prop_id_str: trigger_value = trigger_info['value']; break
        trigger_type = triggered_id_dict.get('type')
        trigger_report_type = triggered_id_dict.get('report_type')

        if trigger_type == 'report-modal-control-store':
            if control_data and control_data.get('modal_type') == 'close':
                close_report_type = control_data.get('report_type')
                print(f"Closing modals for {close_report_type} via control store")
                if close_report_type == 'bug': bug_detail_open, bug_admin_open = False, False
                elif close_report_type == 'request': req_detail_open, req_admin_open = False, False
            else: raise PreventUpdate

        else:
            if trigger_type in ['close-bug-detail-modal', 'cancel-bug-admin-modal', 'close-request-detail-modal', 'cancel-request-admin-modal']:
                if not trigger_value: raise PreventUpdate
                print(f"Closing modal via button: {trigger_type}")
                if 'bug' in trigger_type: bug_detail_open, bug_admin_open = False, False
                elif 'request' in trigger_type: req_detail_open, req_admin_open = False, False

            elif trigger_type == 'report-item':
                if not trigger_value:
                    print(f"Closing modals due to n_clicks=0 for {trigger_report_type}")
                    if trigger_report_type == 'bug': bug_detail_open, bug_admin_open, store_data_out = False, False, None
                    elif trigger_report_type == 'request': req_detail_open, req_admin_open, store_data_out = False, False, None
                else:
                    report_id = triggered_id_dict.get('index')
                    print(f"Item click: report_id={report_id}, report_type={trigger_report_type}")
                    get_func = get_all_bug_reports if trigger_report_type == 'bug' else get_all_feature_requests
                    reports = get_func()
                    report = next((r for r in reports if r['id'] == report_id), None)

                    if not report:
                        print("Report not found.")
                        error_alert = dbc.Alert("報告データが見つかりません。", color="danger")
                        if trigger_report_type == 'bug': bug_detail_open, bug_detail_title, bug_detail_body, bug_admin_open = True, "エラー", error_alert, False
                        elif trigger_report_type == 'request': req_detail_open, req_detail_title, req_detail_body, req_admin_open = True, "エラー", error_alert, False
                    else:
                        is_admin = user_info and user_info.get('role') == 'admin'
                        store_data_out = {'id': report_id, 'type': trigger_report_type}

                        if is_admin:
                            print("Admin user - opening admin modal")
                            details = html.Div([ html.H5(report['title']), html.Small(f"報告者: {report['reporter_username']} | 日時: {report['report_date']}"), dbc.Card(dbc.CardBody(report['description']), className="mt-2 mb-3 bg-light") ])
                            if trigger_report_type == 'bug':
                                bug_detail_open, bug_admin_open = False, True
                                bug_admin_display, bug_status_val, bug_message_val = details, report['status'], report.get('resolution_message', '')
                                req_detail_open, req_admin_open = False, False
                            elif trigger_report_type == 'request':
                                req_detail_open, req_admin_open = False, True
                                req_admin_display, req_status_val, req_message_val = details, report['status'], report.get('resolution_message', '')
                                bug_detail_open, bug_admin_open = False, False
                        else:
                            print("Non-admin user - opening detail modal")
                            body = [ html.P([html.Strong("報告者: "), report['reporter_username']]), html.P([html.Strong("報告日時: "), report['report_date']]), html.Hr(), html.P(report['description'], style={'whiteSpace': 'pre-wrap'}), ]
                            if report['status'] in ['対応済', '見送り'] and report.get('resolution_message'):
                                status_label = "対応内容" if report['status'] == '対応済' else "コメント"
                                body.extend([ html.Hr(), html.Strong(f"{status_label}:"), dbc.Card(dbc.CardBody(report['resolution_message']), className="mt-2 bg-light") ])
                            if trigger_report_type == 'bug':
                                bug_detail_open, bug_admin_open = True, False
                                bug_detail_title, bug_detail_body = report['title'], body
                                req_detail_open, req_admin_open = False, False
                            elif trigger_report_type == 'request':
                                req_detail_open, req_admin_open = True, False
                                req_detail_title, req_detail_body = report['title'], body
                                bug_detail_open, bug_admin_open = False, False
            else: raise PreventUpdate

        return (bug_detail_open, bug_detail_title, bug_detail_body, bug_admin_open, bug_admin_display, bug_status_val, bug_message_val,
                req_detail_open, req_detail_title, req_detail_body, req_admin_open, req_admin_display, req_status_val, req_message_val,
                store_data_out)


    # --- 管理者によるステータス更新コールバック (変更なし) ---
    def create_save_status_callback(report_type_match):
        @app.callback(
            Output(f'{report_type_match}-admin-alert', 'children'),
            Output(f'{report_type_match}-admin-alert', 'is_open'),
            Output('toast-trigger', 'data', allow_duplicate=True),
            Output('report-update-trigger', 'data', allow_duplicate=True),
            Output('report-modal-control-store', 'data', allow_duplicate=True),
            Input(f'save-{report_type_match}-status-btn', 'n_clicks'),
            State('editing-report-store', 'data'),
            State(f'{report_type_match}-status-dropdown', 'value'),
            State(f'{report_type_match}-resolution-message-input', 'value'),
            prevent_initial_call=True
        )
        def save_status(n_clicks, store_data, status, message):
            if not n_clicks or not store_data or store_data.get('type') != report_type_match: raise PreventUpdate
            report_id = store_data.get('id')
            if report_id is None: raise PreventUpdate

            update_func = update_bug_status if report_type_match == 'bug' else update_request_status
            resolve_bug_func = resolve_bug
            resolve_request_func = resolve_request

            if status == '対応済':
                if report_type_match == 'bug': success, msg = resolve_bug_func(report_id, message)
                else: success, msg = resolve_request_func(report_id, message, status)
            elif status == '見送り' and report_type_match == 'request': success, msg = resolve_request_func(report_id, message, status)
            elif status in ['未対応', '対応中']: success, msg = update_func(report_id, status)
            else: success = False; msg = "無効なステータスです。"

            if success:
                toast_data = {'timestamp': datetime.now().isoformat(), 'message': msg, 'source': f'{report_type_match}_report'}
                update_trigger = {'timestamp': datetime.now().isoformat(), 'type': report_type_match}
                close_modal_data = {'report_type': report_type_match, 'modal_type': 'close', 'is_open': False, 'timestamp': datetime.now().isoformat()}
                return "", False, toast_data, update_trigger, close_modal_data
            else: return dbc.Alert(f"エラー: {msg}", color="danger"), True, no_update, no_update, no_update

    create_save_status_callback('bug')
    create_save_status_callback('request')