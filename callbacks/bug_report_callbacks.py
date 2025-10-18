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
        [State('report-tabs', 'active_tab'),
         State('auth-store', 'data'),
         State('bug-title', 'value'), State('bug-description', 'value'),
         State('request-title', 'value'), State('request-description', 'value')],
        prevent_initial_call=True
    )
    def submit_report_or_request(bug_clicks, request_clicks, active_tab, user_info,
                                 bug_title, bug_desc, req_title, req_desc):
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
                if status == '対応済': return "success"
                if status == '対応中': return "warning"
                if status == '見送り': return "dark"
                return "secondary"
            items = [ dbc.ListGroupItem( dbc.Row([ dbc.Col(f"[{r['report_date']}] {r['title']}", width=8), dbc.Col(r['reporter_username'], width=2), dbc.Col(dbc.Badge(r['status'], color=get_status_color(r['status'])), width=2), ], align="center"), id={'type': 'report-item', 'report_type': report_type, 'index': r['id']}, action=True, className="report-list-item", n_clicks=0 ) for r in reports ]
            list_content = dbc.ListGroup(items, flush=True)
        if report_type == 'bug': return list_content, no_update
        else: return no_update, list_content

    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---
    # --- ★★★ コールバック修正 v7 (完全分離) ★★★ ---
    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---

    # --- モーダル開閉 & ID保存 コールバック (report_type ごとに分割) ---
    def register_modal_toggle_callback(report_type_match):
        @app.callback(
            # Output は is_open と editing-id-store のみ
            Output({'type': 'detail-modal', 'report_type': report_type_match}, 'is_open'),
            Output({'type': 'admin-modal', 'report_type': report_type_match}, 'is_open'),
            Output({'type': 'editing-id-store', 'report_type': report_type_match}, 'data'),
            # Input は ALL で監視
            Input({'type': 'report-item', 'report_type': ALL, 'index': ALL}, 'n_clicks'),
            Input({'type': 'close-detail-modal', 'report_type': ALL}, 'n_clicks'),
            Input({'type': 'cancel-admin-modal', 'report_type': ALL}, 'n_clicks'),
            # 保存成功時にも閉じるための Input (Optional)
            Input('report-modal-control-store', 'data'), # Listen to the control store
            State('auth-store', 'data'),
            prevent_initial_call=True
        )
        def handle_modal_toggle(item_clicks, close_detail_clicks, cancel_admin_clicks, control_data, user_info):
            ctx = callback_context
            triggered_prop_id_str = next(iter(ctx.triggered_prop_ids.keys()), None)
            if not triggered_prop_id_str: raise PreventUpdate

            # --- 制御ストアからの指示で閉じる ---
            if triggered_prop_id_str == 'report-modal-control-store.data':
                 if control_data and control_data.get('report_type') == report_type_match and control_data.get('modal_type') == 'close':
                     print(f"Closing modals for {report_type_match} due to control store")
                     return False, False, no_update # Close both, keep id
                 else:
                     raise PreventUpdate # Ignore irrelevant store updates

            # --- 通常のクリックイベント処理 ---
            try:
                triggered_id_str = triggered_prop_id_str.split('.')[0]
                if triggered_id_str.startswith('{'): triggered_id_dict = json.loads(triggered_id_str)
                else: raise PreventUpdate
            except (json.JSONDecodeError, IndexError, AttributeError): raise PreventUpdate

            trigger_type = triggered_id_dict.get('type')
            trigger_report_type = triggered_id_dict.get('report_type')

            # 関係ない report_type のトリガーは無視
            if trigger_report_type != report_type_match:
                raise PreventUpdate

            # トリガーの値 (n_clicks) を取得
            trigger_value = None
            for trigger_info in ctx.triggered:
                if trigger_info['prop_id'] == triggered_prop_id_str:
                    trigger_value = trigger_info['value']; break

            # --- モーダルを閉じる ---
            if trigger_type in ['close-detail-modal', 'cancel-admin-modal']:
                if not trigger_value: raise PreventUpdate
                print(f"Closing modals for {report_type_match} via button")
                return False, False, no_update # Keep existing report_id in store

            # --- モーダルを開く ---
            if trigger_type == 'report-item':
                if not trigger_value:
                     print(f"Closing modals for {report_type_match} due to n_clicks=0")
                     return False, False, None # Close both and clear id
                report_id = triggered_id_dict.get('index')
                is_admin = user_info and user_info.get('role') == 'admin'
                print(f"Opening {'admin' if is_admin else 'detail'} modal for {report_type_match}, id={report_id}")
                if is_admin:
                    return False, True, report_id # Close detail, open admin, set id
                else:
                    return True, False, report_id # Open detail, close admin, set id

            raise PreventUpdate

    # 各 report_type に対してコールバックを登録
    register_modal_toggle_callback('bug')
    register_modal_toggle_callback('request')


    # --- モーダル内容更新 コールバック (report_type, modal_type ごとに分割) ---
    def register_modal_content_callback(report_type_match, modal_type_match):
        is_admin_modal = modal_type_match == 'admin'

        @app.callback(
            # Admin Modal Outputs
            Output({'type': 'admin-detail-display', 'report_type': report_type_match}, 'children') if is_admin_modal else Output({'type': 'detail-modal-title', 'report_type': report_type_match}, 'children'),
            Output({'type': 'status-dropdown', 'report_type': report_type_match}, 'value') if is_admin_modal else Output({'type': 'detail-modal-body', 'report_type': report_type_match}, 'children'),
            Output({'type': 'resolution-message-input', 'report_type': report_type_match}, 'value') if is_admin_modal else Output({'type': 'admin-detail-display', 'report_type': report_type_match}, 'children'), # Dummy output for detail
            # Input: Modal is_open status
            Input({'type': modal_type_match + '-modal', 'report_type': report_type_match}, 'is_open'),
            # State: Editing ID
            State({'type': 'editing-id-store', 'report_type': report_type_match}, 'data'),
            prevent_initial_call=True
        )
        def update_modal_content(is_open, report_id):
            if not is_open or report_id is None:
                # モーダルが閉じたか、IDがない場合は内容をクリアまたは更新しない
                if is_admin_modal:
                    return no_update, no_update, no_update
                else:
                    return no_update, no_update, no_update # title, body, dummy

            print(f"Updating content for {report_type_match} {modal_type_match} modal, id={report_id}")

            # データを取得
            get_func = get_all_bug_reports if report_type_match == 'bug' else get_all_feature_requests
            reports = get_func()
            report = next((r for r in reports if r['id'] == report_id), None)

            if not report:
                 # データが見つからない場合のエラー表示
                 error_alert = dbc.Alert("報告データが見つかりません。", color="danger")
                 if is_admin_modal:
                     return error_alert, no_update, no_update # display, status, message
                 else:
                     return "エラー", error_alert, no_update # title, body, dummy

            # 内容をセットして返す
            if is_admin_modal:
                details = html.Div([
                    html.H5(report['title']),
                    html.Small(f"報告者: {report['reporter_username']} | 日時: {report['report_date']}"),
                    dbc.Card(dbc.CardBody(report['description']), className="mt-2 mb-3 bg-light")
                ])
                return details, report['status'], report.get('resolution_message', '')
            else: # Detail Modal
                body = [
                    html.P([html.Strong("報告者: "), report['reporter_username']]),
                    html.P([html.Strong("報告日時: "), report['report_date']]),
                    html.Hr(),
                    html.P(report['description'], style={'whiteSpace': 'pre-wrap'}),
                ]
                if report['status'] in ['対応済', '見送り'] and report.get('resolution_message'):
                    status_label = "対応内容" if report['status'] == '対応済' else "コメント"
                    body.extend([ html.Hr(), html.Strong(f"{status_label}:"), dbc.Card(dbc.CardBody(report['resolution_message']), className="mt-2 bg-light") ])
                return report['title'], body, no_update # title, body, dummy

    # 各 report_type と modal_type の組み合わせでコールバックを登録
    register_modal_content_callback('bug', 'detail')
    register_modal_content_callback('bug', 'admin')
    register_modal_content_callback('request', 'detail')
    register_modal_content_callback('request', 'admin')

    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---
    # --- ★★★ コールバック修正 ここまで ★★★ ---
    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---

    # --- 管理者によるステータス更新コールバック (変更なし) ---
    # Callback 1: Alert 更新用
    @app.callback(
        [Output({'type': 'admin-alert', 'report_type': MATCH}, 'children'),
         Output({'type': 'admin-alert', 'report_type': MATCH}, 'is_open')],
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
        if success: return "", False # 成功時はアラートクリア
        else: return dbc.Alert(f"エラー: {msg}", color="danger"), True # 失敗時はアラート表示

    # Callback 2: Store/Toast 更新用 + モーダル閉じる指示
    @app.callback(
        [Output('toast-trigger', 'data', allow_duplicate=True),
         Output('report-update-trigger', 'data', allow_duplicate=True),
         Output('report-modal-control-store', 'data', allow_duplicate=True)], # モーダル制御ストアを追加
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
        if triggered_index == -1 or not ctx.triggered or ctx.triggered[0].get('value') is None or ctx.triggered[0]['value'] == 0: raise PreventUpdate
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
            # モーダルを閉じるためのデータ
            close_modal_data = {'report_type': report_type, 'modal_type': 'close', 'is_open': False, 'timestamp': datetime.now().isoformat()}
            return toast_data, update_trigger, close_modal_data
        else: return no_update, no_update, no_update # 失敗時は何も返さない