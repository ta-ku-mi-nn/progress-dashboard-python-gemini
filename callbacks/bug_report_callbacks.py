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

    # --- 報告・要望の送信 (変更なし) ---
    @app.callback(
        [Output('bug-submit-alert', 'children'), Output('bug-submit-alert', 'is_open'),
         Output('request-submit-alert', 'children'), Output('request-submit-alert', 'is_open'),
         Output('bug-title', 'value'), Output('bug-description', 'value'),
         Output('request-title', 'value'), Output('request-description', 'value'),
         Output('toast-trigger', 'data', allow_duplicate=True),
         Output('report-update-trigger', 'data')],
        [Input('submit-bug-btn', 'n_clicks'), Input('submit-request-btn', 'n_clicks')],
        [State('report-tabs', 'active_tab'), State('auth-store', 'data'),
         State('bug-title', 'value'), State('bug-description', 'value'),
         State('request-title', 'value'), State('request-description', 'value')],
        prevent_initial_call=True
    )
    def submit_report_or_request(bug_clicks, request_clicks, active_tab, user_info, bug_title, bug_desc, req_title, req_desc):
        ctx = callback_context
        triggered_button_id = ctx.triggered_id
        if not triggered_button_id: raise PreventUpdate
        if not user_info or not user_info.get('username'):
            alert_msg = dbc.Alert("ログインしていません。", color="danger")
            is_bug_submit = triggered_button_id == 'submit-bug-btn'
            bug_alert_out = (alert_msg, True) if is_bug_submit else (no_update, no_update)
            req_alert_out = (alert_msg, True) if not is_bug_submit else (no_update, no_update)
            return bug_alert_out[0], bug_alert_out[1], req_alert_out[0], req_alert_out[1], no_update, no_update, no_update, no_update, no_update, no_update
        reporter = user_info['username']
        is_bug_submit = triggered_button_id == 'submit-bug-btn'
        title, description, report_type = (bug_title, bug_desc, 'bug') if is_bug_submit else (req_title, req_desc, 'request')
        add_func = add_bug_report if report_type == 'bug' else add_feature_request
        if not title or not description:
            alert_msg = dbc.Alert("件名と詳細を入力してください。", color="warning")
            bug_alert_out = (alert_msg, True) if is_bug_submit else (no_update, no_update)
            req_alert_out = (alert_msg, True) if not is_bug_submit else (no_update, no_update)
            return bug_alert_out[0], bug_alert_out[1], req_alert_out[0], req_alert_out[1], no_update, no_update, no_update, no_update, no_update, no_update
        success, message = add_func(reporter, title, description)
        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': f'{report_type}_report'}
            update_trigger = {'timestamp': datetime.now().isoformat(), 'type': report_type}
            bug_title_clear, bug_desc_clear = ("", "") if is_bug_submit else (no_update, no_update)
            req_title_clear, req_desc_clear = ("", "") if not is_bug_submit else (no_update, no_update)
            bug_alert_out = ("", False) if is_bug_submit else (no_update, no_update)
            req_alert_out = ("", False) if not is_bug_submit else (no_update, no_update)
            return bug_alert_out[0], bug_alert_out[1], req_alert_out[0], req_alert_out[1], bug_title_clear, bug_desc_clear, req_title_clear, req_desc_clear, toast_data, update_trigger
        else:
            alert_msg = dbc.Alert(f"エラー: {message}", color="danger")
            bug_alert_out = (alert_msg, True) if is_bug_submit else (no_update, no_update)
            req_alert_out = (alert_msg, True) if not is_bug_submit else (no_update, no_update)
            return bug_alert_out[0], bug_alert_out[1], req_alert_out[0], req_alert_out[1], no_update, no_update, no_update, no_update, no_update, no_update

    # --- 一覧の表示 (変更なし) ---
    @app.callback(
        [Output('bug-list-container', 'children'), Output('request-list-container', 'children')],
        [Input('report-tabs', 'active_tab'), Input('report-update-trigger', 'data')]
    )
    def update_report_list(active_tab, update_trigger):
        # (内容は変更なし)
        ctx = callback_context
        if not ctx.triggered_id and active_tab is None: raise PreventUpdate
        if not active_tab: raise PreventUpdate
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
        if report_type == 'bug': return list_content, no_update
        else: return no_update, list_content

    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---
    # --- ★★★ コールバック修正 v9 (単一コールバック) ★★★ ---
    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---
    @app.callback(
        # --- Outputs for ALL modals (simple IDs) ---
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
        # --- Shared Store Output ---
        Output('editing-report-store', 'data', allow_duplicate=True),
        # --- Inputs (ALL pattern for items, simple IDs for close buttons) ---
        Input({'type': 'report-item', 'report_type': ALL, 'index': ALL}, 'n_clicks'),
        Input('close-bug-detail-modal', 'n_clicks'),
        Input('cancel-bug-admin-modal', 'n_clicks'),
        Input('close-request-detail-modal', 'n_clicks'),
        Input('cancel-request-admin-modal', 'n_clicks'),
        # --- Input for closing after save ---
        Input('report-modal-control-store', 'data'),
        # --- State ---
        State('auth-store', 'data'),
        prevent_initial_call=True
    )
    def handle_modal_toggle_final(item_clicks, close_bug_detail, cancel_bug_admin,
                                  close_req_detail, cancel_req_admin, control_data, user_info):
        ctx = callback_context
        triggered_prop_id_str = next(iter(ctx.triggered_prop_ids.keys()), None)
        if not triggered_prop_id_str: raise PreventUpdate

        # --- Initialize all outputs to no_update ---
        # Bug Detail
        bug_detail_open = no_update
        bug_detail_title = no_update
        bug_detail_body = no_update
        # Bug Admin
        bug_admin_open = no_update
        bug_admin_display = no_update
        bug_status_val = no_update
        bug_message_val = no_update
        # Request Detail
        req_detail_open = no_update
        req_detail_title = no_update
        req_detail_body = no_update
        # Request Admin
        req_admin_open = no_update
        req_admin_display = no_update
        req_status_val = no_update
        req_message_val = no_update
        # Store
        store_data_out = no_update

        # --- Determine Trigger ---
        trigger_value = None
        triggered_id_dict = None
        is_pattern_match = False
        try:
            id_str = triggered_prop_id_str.split('.')[0]
            if id_str.startswith('{'):
                triggered_id_dict = json.loads(id_str)
                is_pattern_match = True
            else: triggered_id_dict = {'type': id_str} # Simple ID
        except (json.JSONDecodeError, IndexError, AttributeError): raise PreventUpdate
        for trigger_info in ctx.triggered:
            if trigger_info['prop_id'] == triggered_prop_id_str: trigger_value = trigger_info['value']; break
        trigger_type = triggered_id_dict.get('type')
        trigger_report_type = triggered_id_dict.get('report_type') # None for simple IDs

        # --- Handle Close Signal from Control Store ---
        if trigger_type == 'report-modal-control-store':
            if control_data and control_data.get('modal_type') == 'close':
                close_report_type = control_data.get('report_type')
                print(f"Closing modals for {close_report_type} via control store")
                if close_report_type == 'bug': bug_detail_open, bug_admin_open = False, False
                elif close_report_type == 'request': req_detail_open, req_admin_open = False, False
                # Keep store data as is
            else: raise PreventUpdate # Ignore other store updates

        # --- Handle Button/Item Clicks ---
        else:
            # --- Closing Modals ---
            if trigger_type in ['close-bug-detail-modal', 'cancel-bug-admin-modal',
                                'close-request-detail-modal', 'cancel-request-admin-modal']:
                if not trigger_value: raise PreventUpdate
                print(f"Closing modal via button: {trigger_type}")
                if 'bug' in trigger_type: bug_detail_open, bug_admin_open = False, False
                elif 'request' in trigger_type: req_detail_open, req_admin_open = False, False
                # Keep store data as is

            # --- Opening Modals ---
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
                        store_data_out = {'id': report_id, 'type': trigger_report_type} # Set store data

                        if is_admin:
                            print("Admin user - opening admin modal")
                            details = html.Div([ html.H5(report['title']), html.Small(f"報告者: {report['reporter_username']} | 日時: {report['report_date']}"), dbc.Card(dbc.CardBody(report['description']), className="mt-2 mb-3 bg-light") ])
                            if trigger_report_type == 'bug':
                                bug_detail_open, bug_admin_open = False, True
                                bug_admin_display, bug_status_val, bug_message_val = details, report['status'], report.get('resolution_message', '')
                                # Ensure other type's modals are closed
                                req_detail_open, req_admin_open = False, False
                            elif trigger_report_type == 'request':
                                req_detail_open, req_admin_open = False, True
                                req_admin_display, req_status_val, req_message_val = details, report['status'], report.get('resolution_message', '')
                                # Ensure other type's modals are closed
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
                                # Ensure other type's modals are closed
                                req_detail_open, req_admin_open = False, False
                            elif trigger_report_type == 'request':
                                req_detail_open, req_admin_open = True, False
                                req_detail_title, req_detail_body = report['title'], body
                                # Ensure other type's modals are closed
                                bug_detail_open, bug_admin_open = False, False
            else:
                 # Unhandled trigger type
                 raise PreventUpdate


        # Return all output values
        return (
            bug_detail_open, bug_detail_title, bug_detail_body,
            bug_admin_open, bug_admin_display, bug_status_val, bug_message_val,
            req_detail_open, req_detail_title, req_detail_body,
            req_admin_open, req_admin_display, req_status_val, req_message_val,
            store_data_out
        )


    # --- 管理者によるステータス更新コールバック (ID単純化) ---
    def create_save_status_callback(report_type_match):
        @app.callback(
            # Alert Outputs (Specific ID)
            Output(f'{report_type_match}-admin-alert', 'children'),
            Output(f'{report_type_match}-admin-alert', 'is_open'),
            # Store/Toast Outputs (Allow duplicate)
            Output('toast-trigger', 'data', allow_duplicate=True),
            Output('report-update-trigger', 'data', allow_duplicate=True),
            Output('report-modal-control-store', 'data', allow_duplicate=True), # To close modal
            # Input (Specific ID)
            Input(f'save-{report_type_match}-status-btn', 'n_clicks'),
            # State (Specific ID + Shared Store)
            State('editing-report-store', 'data'),
            State(f'{report_type_match}-status-dropdown', 'value'),
            State(f'{report_type_match}-resolution-message-input', 'value'),
            prevent_initial_call=True
        )
        def save_status(n_clicks, store_data, status, message):
            # Check click and if store data matches the report type for this callback
            if not n_clicks or not store_data or store_data.get('type') != report_type_match:
                raise PreventUpdate

            report_id = store_data.get('id')
            if report_id is None: raise PreventUpdate

            update_func = update_bug_status if report_type_match == 'bug' else update_request_status
            resolve_bug_func = resolve_bug # resolve_bug は引数2つ
            resolve_request_func = resolve_request # resolve_request は引数3つ

            if status == '対応済':
                if report_type_match == 'bug':
                    success, msg = resolve_bug_func(report_id, message) # 引数2つで呼び出し
                else: # report_type_match == 'request'
                    success, msg = resolve_request_func(report_id, message, status) # 引数3つで呼び出し
            elif status == '見送り' and report_type_match == 'request': # 見送りは request のみ
                 success, msg = resolve_request_func(report_id, message, status) # 引数3つで呼び出し
            elif status in ['未対応', '対応中']:
                success, msg = update_func(report_id, status) # message は不要
            else:
                success = False; msg = "無効なステータスです。"

            if success:
                toast_data = {'timestamp': datetime.now().isoformat(), 'message': msg, 'source': f'{report_type_match}_report'}
                update_trigger = {'timestamp': datetime.now().isoformat(), 'type': report_type_match}
                # ★★★ モーダルを閉じるためのデータ ★★★
                close_modal_data = {'report_type': report_type_match, 'modal_type': 'close', 'is_open': False, 'timestamp': datetime.now().isoformat()}
                # アラートクリア、Toast表示、リスト更新トリガー発行、モーダル閉じる指示
                return "", False, toast_data, update_trigger, close_modal_data
            else:
                # 失敗時はアラート表示のみ
                return dbc.Alert(f"エラー: {msg}", color="danger"), True, no_update, no_update, no_update

    # Register save status callbacks
    create_save_status_callback('bug')
    create_save_status_callback('request')