# callbacks/bug_report_callbacks.py

from dash import Input, Output, State, html, no_update, callback_context, ALL, MATCH, clientside_callback # clientside_callback をインポート
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
    # --- ★★★ コールバック修正 v6 (Python + Clientside) ★★★ ---
    # --- ★★★★★★★★★★★★★★★★★★★★★★★★ ---

    # --- Python Callback: モーダル制御情報をStoreに出力 ---
    @app.callback(
        Output('report-modal-control-store', 'data'),
        # Inputs using ALL
        Input({'type': 'report-item', 'report_type': ALL, 'index': ALL}, 'n_clicks'),
        Input({'type': 'close-detail-modal', 'report_type': ALL}, 'n_clicks'),
        Input({'type': 'cancel-admin-modal', 'report_type': ALL}, 'n_clicks'),
        State('auth-store', 'data'),
        prevent_initial_call=True
    )
    def update_modal_control_store(item_clicks, close_detail_clicks, cancel_admin_clicks, user_info):
        ctx = callback_context
        triggered_prop_id_str = next(iter(ctx.triggered_prop_ids.keys()), None)
        if not triggered_prop_id_str: raise PreventUpdate

        try:
            triggered_id_str = triggered_prop_id_str.split('.')[0]
            if triggered_id_str.startswith('{'): triggered_id_dict = json.loads(triggered_id_str)
            else: raise PreventUpdate
        except (json.JSONDecodeError, IndexError, AttributeError): raise PreventUpdate

        trigger_type = triggered_id_dict.get('type')
        trigger_report_type = triggered_id_dict.get('report_type')

        # Find the actual trigger value (n_clicks)
        trigger_value = None
        for trigger_info in ctx.triggered:
            if trigger_info['prop_id'] == triggered_prop_id_str:
                trigger_value = trigger_info['value']
                break

        # --- Closing Modals ---
        if trigger_type in ['close-detail-modal', 'cancel-admin-modal']:
            if not trigger_value: raise PreventUpdate # Only react on actual click
            print(f"Python: Closing modal for {trigger_report_type}")
            # Signal to close all modals of the triggered type
            return {'report_type': trigger_report_type, 'modal_type': 'close', 'is_open': False, 'timestamp': datetime.now().isoformat()}

        # --- Opening Modals (report-item click) ---
        if trigger_type == 'report-item':
            if not trigger_value:
                 # Signal to close modals if n_clicks becomes 0
                 print(f"Python: Closing modal due to n_clicks=0 for {trigger_report_type}")
                 return {'report_type': trigger_report_type, 'modal_type': 'close', 'is_open': False, 'timestamp': datetime.now().isoformat()}

            report_id = triggered_id_dict.get('index')
            print(f"Python: Handling item click for report_id={report_id}, report_type={trigger_report_type}")

            get_func = get_all_bug_reports if trigger_report_type == 'bug' else get_all_feature_requests
            reports = get_func()
            report = next((r for r in reports if r['id'] == report_id), None)

            modal_data = {'report_type': trigger_report_type, 'is_open': False, 'timestamp': datetime.now().isoformat()} # Default to closed

            if report:
                is_admin = user_info and user_info.get('role') == 'admin'
                if is_admin:
                    print("Python: Preparing admin modal data")
                    modal_data.update({
                        'modal_type': 'admin',
                        'is_open': True,
                        'report_id': report_id,
                        'status': report['status'],
                        'resolution_message': report.get('resolution_message', ''),
                        'details_title': report['title'],
                        'details_reporter': report['reporter_username'],
                        'details_date': report['report_date'],
                        'details_description': report['description']
                    })
                else:
                    print("Python: Preparing detail modal data")
                    modal_data.update({
                        'modal_type': 'detail',
                        'is_open': True,
                        'title': report['title'],
                        'reporter': report['reporter_username'],
                        'date': report['report_date'],
                        'description': report['description'],
                        'status': report['status'],
                        'resolution_message': report.get('resolution_message', '')
                    })
            else:
                 print("Python: Report not found, preparing error detail modal")
                 modal_data.update({
                    'modal_type': 'detail',
                    'is_open': True,
                    'title': 'エラー',
                    'error_message': '報告が見つかりません。' # Send specific error message
                 })
            return modal_data

        raise PreventUpdate


    # --- Clientside Callbacks: モーダルの表示/内容更新 ---

    # --- Bug Detail Modal ---
    clientside_callback(
        """
        function(controlData) {
            // console.log("CS: Bug Detail Modal triggered", controlData);
            if (!controlData || controlData.report_type !== 'bug') {
                return [dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update];
            }
            if (controlData.modal_type === 'close') {
                return [false, dash_clientside.no_update, dash_clientside.no_update];
            }
            if (controlData.modal_type === 'detail') {
                if (controlData.error_message) {
                    // Display error in modal body
                    return [
                        controlData.is_open,
                        controlData.title,
                        // Simple error display using dbc.Alert structure (adapt if using html directly)
                        window.dash_clientside.React.createElement(
                            window.dash_bootstrap_components.Alert, {color: "danger"}, controlData.error_message
                        )
                    ];
                }
                let bodyContent = [
                    window.dash_clientside.React.createElement('p', null, [window.dash_clientside.React.createElement('strong', null, '報告者: '), controlData.reporter]),
                    window.dash_clientside.React.createElement('p', null, [window.dash_clientside.React.createElement('strong', null, '報告日時: '), controlData.date]),
                    window.dash_clientside.React.createElement('hr'),
                    window.dash_clientside.React.createElement('p', {style: {whiteSpace: 'pre-wrap'}}, controlData.description),
                ];
                if ((controlData.status === '対応済' || controlData.status === '見送り') && controlData.resolution_message) {
                    const statusLabel = controlData.status === '対応済' ? '対応内容' : 'コメント';
                    bodyContent.push(window.dash_clientside.React.createElement('hr'));
                    bodyContent.push(window.dash_clientside.React.createElement('strong', null, statusLabel + ':'));
                    // Assuming dbc components are available globally via dash-bootstrap-components
                    bodyContent.push(
                        window.dash_clientside.React.createElement(
                            window.dash_bootstrap_components.Card, {className: "mt-2 bg-light"},
                            window.dash_clientside.React.createElement(window.dash_bootstrap_components.CardBody, null, controlData.resolution_message)
                        )
                    );
                }
                return [controlData.is_open, controlData.title, bodyContent];
            }
            // If modal_type is 'admin' or something else, ensure this detail modal is closed
            return [false, dash_clientside.no_update, dash_clientside.no_update];
        }
        """,
        Output({'type': 'detail-modal', 'report_type': 'bug'}, 'is_open'),
        Output({'type': 'detail-modal-title', 'report_type': 'bug'}, 'children'),
        Output({'type': 'detail-modal-body', 'report_type': 'bug'}, 'children'),
        Input('report-modal-control-store', 'data')
    )

    # --- Request Detail Modal ---
    clientside_callback(
        """
        function(controlData) {
            // console.log("CS: Request Detail Modal triggered", controlData);
            if (!controlData || controlData.report_type !== 'request') {
                return [dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update];
            }
            if (controlData.modal_type === 'close') {
                return [false, dash_clientside.no_update, dash_clientside.no_update];
            }
            if (controlData.modal_type === 'detail') {
                 if (controlData.error_message) {
                    return [
                        controlData.is_open,
                        controlData.title,
                         window.dash_clientside.React.createElement(
                            window.dash_bootstrap_components.Alert, {color: "danger"}, controlData.error_message
                        )
                    ];
                }
                let bodyContent = [
                    window.dash_clientside.React.createElement('p', null, [window.dash_clientside.React.createElement('strong', null, '報告者: '), controlData.reporter]),
                    window.dash_clientside.React.createElement('p', null, [window.dash_clientside.React.createElement('strong', null, '報告日時: '), controlData.date]),
                    window.dash_clientside.React.createElement('hr'),
                    window.dash_clientside.React.createElement('p', {style: {whiteSpace: 'pre-wrap'}}, controlData.description),
                ];
                if ((controlData.status === '対応済' || controlData.status === '見送り') && controlData.resolution_message) {
                    const statusLabel = controlData.status === '対応済' ? '対応内容' : 'コメント';
                    bodyContent.push(window.dash_clientside.React.createElement('hr'));
                    bodyContent.push(window.dash_clientside.React.createElement('strong', null, statusLabel + ':'));
                    bodyContent.push(
                        window.dash_clientside.React.createElement(
                            window.dash_bootstrap_components.Card, {className: "mt-2 bg-light"},
                            window.dash_clientside.React.createElement(window.dash_bootstrap_components.CardBody, null, controlData.resolution_message)
                        )
                    );
                }
                return [controlData.is_open, controlData.title, bodyContent];
            }
             // If modal_type is 'admin' or something else, ensure this detail modal is closed
            return [false, dash_clientside.no_update, dash_clientside.no_update];
        }
        """,
        Output({'type': 'detail-modal', 'report_type': 'request'}, 'is_open'),
        Output({'type': 'detail-modal-title', 'report_type': 'request'}, 'children'),
        Output({'type': 'detail-modal-body', 'report_type': 'request'}, 'children'),
        Input('report-modal-control-store', 'data')
    )

    # --- Bug Admin Modal ---
    clientside_callback(
        """
        function(controlData) {
            // console.log("CS: Bug Admin Modal triggered", controlData);
            if (!controlData || controlData.report_type !== 'bug') {
                return [dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update];
            }
            if (controlData.modal_type === 'close') {
                return [false, dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update];
            }
            if (controlData.modal_type === 'admin') {
                // Construct admin details display using React.createElement
                const details = window.dash_clientside.React.createElement('div', null, [
                    window.dash_clientside.React.createElement('h5', null, controlData.details_title),
                    window.dash_clientside.React.createElement('small', null, `報告者: ${controlData.details_reporter} | 日時: ${controlData.details_date}`),
                    window.dash_clientside.React.createElement(
                        window.dash_bootstrap_components.Card, {className: "mt-2 mb-3 bg-light"},
                        window.dash_clientside.React.createElement(window.dash_bootstrap_components.CardBody, null, controlData.details_description)
                    )
                ]);
                return [
                    controlData.is_open,
                    details,
                    controlData.report_id,
                    controlData.status,
                    controlData.resolution_message
                ];
            }
             // If modal_type is 'detail' or something else, ensure this admin modal is closed
            return [false, dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update];
        }
        """,
        Output({'type': 'admin-modal', 'report_type': 'bug'}, 'is_open'),
        Output({'type': 'admin-detail-display', 'report_type': 'bug'}, 'children'), # Update content
        Output({'type': 'editing-id-store', 'report_type': 'bug'}, 'data'),         # Update store
        Output({'type': 'status-dropdown', 'report_type': 'bug'}, 'value'),       # Update dropdown value
        Output({'type': 'resolution-message-input', 'report_type': 'bug'}, 'value'), # Update textarea value
        Input('report-modal-control-store', 'data')
    )

    # --- Request Admin Modal ---
    clientside_callback(
        """
        function(controlData) {
            // console.log("CS: Request Admin Modal triggered", controlData);
            if (!controlData || controlData.report_type !== 'request') {
                 return [dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update];
            }
             if (controlData.modal_type === 'close') {
                return [false, dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update];
            }
            if (controlData.modal_type === 'admin') {
                 const details = window.dash_clientside.React.createElement('div', null, [
                    window.dash_clientside.React.createElement('h5', null, controlData.details_title),
                    window.dash_clientside.React.createElement('small', null, `報告者: ${controlData.details_reporter} | 日時: ${controlData.details_date}`),
                    window.dash_clientside.React.createElement(
                        window.dash_bootstrap_components.Card, {className: "mt-2 mb-3 bg-light"},
                        window.dash_clientside.React.createElement(window.dash_bootstrap_components.CardBody, null, controlData.details_description)
                    )
                ]);
                return [
                    controlData.is_open,
                    details,
                    controlData.report_id,
                    controlData.status,
                    controlData.resolution_message
                ];
            }
            // If modal_type is 'detail' or something else, ensure this admin modal is closed
            return [false, dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update, dash_clientside.no_update];
        }
        """,
        Output({'type': 'admin-modal', 'report_type': 'request'}, 'is_open'),
        Output({'type': 'admin-detail-display', 'report_type': 'request'}, 'children'),
        Output({'type': 'editing-id-store', 'report_type': 'request'}, 'data'),
        Output({'type': 'status-dropdown', 'report_type': 'request'}, 'value'),
        Output({'type': 'resolution-message-input', 'report_type': 'request'}, 'value'),
        Input('report-modal-control-store', 'data')
    )


    # --- 管理者によるステータス更新コールバック (変更なし) ---
    @app.callback(
        [Output({'type': 'admin-alert', 'report_type': MATCH}, 'children'),
         Output({'type': 'admin-alert', 'report_type': MATCH}, 'is_open'),
         # ★★★ モーダルを閉じるOutputは Clientside に任せるので削除 ★★★
         # Output({'type': 'admin-modal', 'report_type': MATCH}, 'is_open', allow_duplicate=True)],
         ], # ★★★ 削除後のカンマに注意 ★★★
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

        # ★★★ is_open の Output を削除したので、戻り値も変更 ★★★
        if success:
             # 成功時はアラートをクリアするだけ (モーダルは閉じない)
             return "", False #, False # 最後の False を削除
        else:
             # 失敗時はアラート表示 (モーダルは開いたまま)
             return dbc.Alert(f"エラー: {msg}", color="danger"), True #, True # 最後の True を削除

    @app.callback(
        [Output('toast-trigger', 'data', allow_duplicate=True),
         Output('report-update-trigger', 'data', allow_duplicate=True),
         # ★★★ 保存成功時に Clientside にモーダルを閉じるよう指示する ★★★
         Output('report-modal-control-store', 'data', allow_duplicate=True)],
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
            # ★★★ モーダルを閉じるためのデータ ★★★
            close_modal_data = {'report_type': report_type, 'modal_type': 'close', 'is_open': False, 'timestamp': datetime.now().isoformat()}
            return toast_data, update_trigger, close_modal_data
        else:
             # 失敗時はモーダル制御データは送らない
             return no_update, no_update, no_update