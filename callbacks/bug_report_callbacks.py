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
        [Output('bug-list-container', 'children'),
         Output('request-list-container', 'children')],
        [Input('report-tabs', 'active_tab'),
         Input('report-update-trigger', 'data')]
    )
    def update_report_list(active_tab, update_trigger):
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
    # --- ★★★ コールバック修正 v8 (完全分離・ID単純化) ★★★ ---
    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---

    # --- モーダル開閉 & ID保存 コールバック (モーダルごとに作成) ---
    def create_toggle_callback(modal_report_type, admin_modal_id, detail_modal_id, editing_store_id):
        @app.callback(
            Output(detail_modal_id, 'is_open'),
            Output(admin_modal_id, 'is_open'),
            Output(editing_store_id, 'data'),
            # Inputs using ALL (pattern matching for items, simple IDs for close buttons)
            Input({'type': 'report-item', 'report_type': ALL, 'index': ALL}, 'n_clicks'),
            Input(f'close-{modal_report_type}-detail-modal', 'n_clicks'),
            Input(f'cancel-{modal_report_type}-admin-modal', 'n_clicks'),
            # Input to react to successful save/close signal
            Input('report-modal-control-store', 'data'),
            State('auth-store', 'data'),
            prevent_initial_call=True
        )
        def toggle_modal(item_clicks, close_detail_click, cancel_admin_click, control_data, user_info):
            ctx = callback_context
            triggered_prop_id_str = next(iter(ctx.triggered_prop_ids.keys()), None)
            if not triggered_prop_id_str: raise PreventUpdate

            # --- Handle close signal from control store ---
            if triggered_prop_id_str == 'report-modal-control-store.data':
                if control_data and control_data.get('report_type') == modal_report_type and control_data.get('modal_type') == 'close':
                    print(f"Closing modals for {modal_report_type} via control store")
                    return False, False, no_update # Keep store data
                else:
                    raise PreventUpdate

            # --- Handle button/item clicks ---
            trigger_value = None
            triggered_id_dict = None
            is_pattern_match = False

            # Try parsing pattern-matching ID first
            try:
                id_str = triggered_prop_id_str.split('.')[0]
                if id_str.startswith('{'):
                    triggered_id_dict = json.loads(id_str)
                    is_pattern_match = True
            except (json.JSONDecodeError, IndexError, AttributeError):
                triggered_id_dict = None # Not a pattern-matching ID

            # If not pattern match, it's a simple button ID
            if not is_pattern_match:
                triggered_id_dict = {'type': triggered_prop_id_str.split('.')[0]} # Use the simple ID as type

            # Get trigger value (n_clicks)
            for trigger_info in ctx.triggered:
                if trigger_info['prop_id'] == triggered_prop_id_str:
                    trigger_value = trigger_info['value']; break

            trigger_type = triggered_id_dict.get('type')
            trigger_report_type = triggered_id_dict.get('report_type') # Will be None for simple IDs

            # Ignore triggers for the wrong report_type if it's a pattern-match trigger
            if is_pattern_match and trigger_report_type != modal_report_type:
                raise PreventUpdate

            # --- Closing Modals ---
            # Use simple IDs now for close buttons
            if trigger_type == f'close-{modal_report_type}-detail-modal' or \
               trigger_type == f'cancel-{modal_report_type}-admin-modal':
                if not trigger_value: raise PreventUpdate
                print(f"Closing modals for {modal_report_type} via button")
                return False, False, no_update # Keep store data

            # --- Opening Modals (report-item click) ---
            if trigger_type == 'report-item':
                 if not trigger_value:
                     print(f"Closing modals for {modal_report_type} due to n_clicks=0")
                     return False, False, None # Close and clear store
                 report_id = triggered_id_dict.get('index')
                 is_admin = user_info and user_info.get('role') == 'admin'
                 print(f"Opening {'admin' if is_admin else 'detail'} modal for {modal_report_type}, id={report_id}")
                 if is_admin: return False, True, {'id': report_id, 'type': modal_report_type} # Close detail, open admin, set store
                 else: return True, False, {'id': report_id, 'type': modal_report_type} # Open detail, close admin, set store

            raise PreventUpdate

    # Register the toggle callbacks
    create_toggle_callback('bug', 'bug-admin-modal', 'bug-detail-modal', 'editing-report-store')
    create_toggle_callback('request', 'request-admin-modal', 'request-detail-modal', 'editing-report-store')


    # --- モーダル内容更新 コールバック (モーダルごと、ID単純化) ---
    def create_content_callback(modal_report_type, is_admin_modal):
        modal_id = f"{modal_report_type}-{'admin' if is_admin_modal else 'detail'}-modal"
        store_id = 'editing-report-store'

        outputs = []
        if is_admin_modal:
            outputs = [
                Output(f'{modal_report_type}-admin-detail-display', 'children'),
                Output(f'{modal_report_type}-status-dropdown', 'value'),
                Output(f'{modal_report_type}-resolution-message-input', 'value')
            ]
        else:
            outputs = [
                Output(f'{modal_report_type}-detail-modal-title', 'children'),
                Output(f'{modal_report_type}-detail-modal-body', 'children')
            ]

        @app.callback(
            outputs,
            Input(modal_id, 'is_open'),
            State(store_id, 'data'),
            prevent_initial_call=True
        )
        def update_modal_content(is_open, store_data):
            # Check if the store data is relevant for this modal type
            if not is_open or not store_data or store_data.get('type') != modal_report_type:
                # Return no_update matching the number of outputs
                return [no_update] * len(outputs)

            report_id = store_data.get('id')
            if report_id is None:
                return [no_update] * len(outputs)

            print(f"Updating content for {modal_id}, id={report_id}")

            get_func = get_all_bug_reports if modal_report_type == 'bug' else get_all_feature_requests
            reports = get_func()
            report = next((r for r in reports if r['id'] == report_id), None)

            if not report:
                 error_alert = dbc.Alert("報告データが見つかりません。", color="danger")
                 if is_admin_modal: return error_alert, no_update, no_update
                 else: return "エラー", error_alert

            if is_admin_modal:
                details = html.Div([ html.H5(report['title']), html.Small(f"報告者: {report['reporter_username']} | 日時: {report['report_date']}"), dbc.Card(dbc.CardBody(report['description']), className="mt-2 mb-3 bg-light") ])
                return details, report['status'], report.get('resolution_message', '')
            else: # Detail Modal
                body = [ html.P([html.Strong("報告者: "), report['reporter_username']]), html.P([html.Strong("報告日時: "), report['report_date']]), html.Hr(), html.P(report['description'], style={'whiteSpace': 'pre-wrap'}), ]
                if report['status'] in ['対応済', '見送り'] and report.get('resolution_message'):
                    status_label = "対応内容" if report['status'] == '対応済' else "コメント"
                    body.extend([ html.Hr(), html.Strong(f"{status_label}:"), dbc.Card(dbc.CardBody(report['resolution_message']), className="mt-2 bg-light") ])
                return report['title'], body

    # Register content update callbacks
    create_content_callback('bug', False)    # Bug Detail
    create_content_callback('bug', True)     # Bug Admin
    create_content_callback('request', False) # Request Detail
    create_content_callback('request', True)  # Request Admin


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
            # Check if click happened and store data is relevant
            if not n_clicks or not store_data or store_data.get('type') != report_type_match:
                raise PreventUpdate

            report_id = store_data.get('id')
            if report_id is None:
                raise PreventUpdate # Should have ID if modal was opened correctly

            resolve_func = resolve_bug if report_type_match == 'bug' else resolve_request
            update_func = update_bug_status if report_type_match == 'bug' else update_request_status

            if status in ['対応済', '見送り']:
                success, msg = resolve_func(report_id, message, status)
            elif status in ['未対応', '対応中']:
                success, msg = update_func(report_id, status)
            else:
                success = False; msg = "無効なステータスです。"

            if success:
                toast_data = {'timestamp': datetime.now().isoformat(), 'message': msg, 'source': f'{report_type_match}_report'}
                update_trigger = {'timestamp': datetime.now().isoformat(), 'type': report_type_match}
                close_modal_data = {'report_type': report_type_match, 'modal_type': 'close', 'is_open': False, 'timestamp': datetime.now().isoformat()}
                # Clear alert, send toast, trigger list update, close modal
                return "", False, toast_data, update_trigger, close_modal_data
            else:
                # Show alert, don't send toast/trigger/close
                return dbc.Alert(f"エラー: {msg}", color="danger"), True, no_update, no_update, no_update

    # Register save status callbacks
    create_save_status_callback('bug')
    create_save_status_callback('request')

    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---
    # --- ★★★ コールバック修正 ここまで ★★★ ---
    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---