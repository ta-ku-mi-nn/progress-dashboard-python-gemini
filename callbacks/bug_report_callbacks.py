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
        if not ctx.triggered_id:
            raise PreventUpdate

        if not user_info or not user_info.get('username'):
            alert = dbc.Alert("ログインしていません。", color="danger")
            if active_tab == 'tab-bug-report':
                return alert, True, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            else:
                return no_update, no_update, alert, True, no_update, no_update, no_update, no_update, no_update, no_update

        reporter = user_info['username']
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
    # (変更なし)
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


    # ★★★★★★★★★★★★★★★★★★★★
    # ★★★ 修正箇所 (v3) ★★★
    # ★★★★★★★★★★★★★★★★★★★★
    @app.callback(
        # --- モーダルの Output (MATCH を使用) ---
        Output({'type': 'detail-modal', 'report_type': MATCH}, 'is_open'),
        Output({'type': 'detail-modal-title', 'report_type': MATCH}, 'children'),
        Output({'type': 'detail-modal-body', 'report_type': MATCH}, 'children'),
        Output({'type': 'admin-modal', 'report_type': MATCH}, 'is_open'),
        Output({'type': 'admin-detail-display', 'report_type': MATCH}, 'children'),
        # --- Store の Output (MATCH を使用) ---
        Output({'type': 'editing-id-store', 'report_type': MATCH}, 'data'),
        Output({'type': 'status-dropdown', 'report_type': MATCH}, 'value'),
        Output({'type': 'resolution-message-input', 'report_type': MATCH}, 'value'),
        # --- Input (トリガーとなる要素) ---
        # report-item のクリック (ALL で report_type ごとに監視)
        Input({'type': 'report-item', 'report_type': ALL, 'index': ALL}, 'n_clicks'),
        # 閉じる/キャンセルボタン (★ MATCH に変更 ★)
        Input({'type': 'close-detail-modal', 'report_type': MATCH}, 'n_clicks'),
        Input({'type': 'cancel-admin-modal', 'report_type': MATCH}, 'n_clicks'),
        # --- State ---
        State('auth-store', 'data'),
        prevent_initial_call=True # 初回読み込み時は実行しない
    )
    def handle_modal_toggle_v3(item_clicks, close_detail_clicks, cancel_admin_clicks, user_info):
        ctx = callback_context

        triggered_prop_id_str = ctx.triggered_prop_ids.get('.')
        if not triggered_prop_id_str:
            raise PreventUpdate

        # 現在のコールバックの MATCH コンテキストを取得
        # ctx.outputs_list[0][0]['id'] は {'type': '...', 'report_type': '...'}
        current_match_context = ctx.outputs_list[0][0]['id']
        current_report_type = current_match_context['report_type']

        # トリガーIDを解析
        try:
            triggered_id_str = triggered_prop_id_str.split('.')[0]
            if triggered_id_str.startswith('{'):
                 triggered_id_dict = json.loads(triggered_id_str)
            else:
                 # 通常の文字列IDの場合 (このコールバックでは発生しないはずだが念のため)
                 triggered_id_dict = {'type': triggered_id_str} # ダミーのtype
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Error parsing triggered ID: {e}, ID string: {triggered_prop_id_str}")
            raise PreventUpdate

        trigger_type = triggered_id_dict.get('type')
        # トリガーが report-item (ALL) の場合、IDから report_type を取得
        # トリガーが close/cancel ボタン (MATCH) の場合、current_report_type を使う
        trigger_report_type = triggered_id_dict.get('report_type', current_report_type)

        print(f"Callback Context: {current_report_type}, Trigger Type: {trigger_type}, Trigger Report Type: {trigger_report_type}") # デバッグ用

        # --- モーダルを閉じる処理 (MATCH トリガー) ---
        if trigger_type in ['close-detail-modal', 'cancel-admin-modal']:
             # このコールバックインスタンスが担当する report_type のボタンが押された場合のみ閉じる
             if trigger_report_type == current_report_type:
                 print(f"Closing modal for {current_report_type}")
                 return False, no_update, no_update, False, no_update, no_update, no_update, no_update
             else:
                 # 関係ない report_type のボタンが押されても、このインスタンスは反応しない
                 raise PreventUpdate

        # --- リスト項目クリック時の処理 (ALL トリガー) ---
        if trigger_type == 'report-item':
            # このコールバックインスタンスが担当する report_type の項目がクリックされたか？
            if trigger_report_type != current_report_type:
                # 違う場合は、このインスタンスは PreventUpdate
                print(f"Ignoring item click for {trigger_report_type} in {current_report_type} context.")
                raise PreventUpdate

            # クリックイベントの値 (n_clicks) を取得
            clicked_n_clicks = ctx.triggered[0]['value'] if ctx.triggered else None
            if not clicked_n_clicks:
                # クリック値がない (初期状態など) 場合は、モーダルを確実に閉じるか no_update
                print("Click value is None or 0, closing/preventing update.")
                return False, no_update, no_update, False, no_update, no_update, no_update, no_update # 確実に閉じる

            # データを取得してモーダルを開く処理 (v2 と同様)
            report_id = triggered_id_dict.get('index')
            print(f"Handling item click for report_id={report_id}, report_type={current_report_type}")

            get_func = get_all_bug_reports if current_report_type == 'bug' else get_all_feature_requests
            reports = get_func()
            report = next((r for r in reports if r['id'] == report_id), None)

            if not report:
                print("Report not found.")
                return True, "エラー", dbc.Alert("報告が見つかりません。", color="danger"), False, no_update, no_update, no_update, no_update

            is_admin = user_info and user_info.get('role') == 'admin'

            if is_admin:
                print("Admin user - opening admin modal")
                details = html.Div([
                    html.H5(report['title']),
                    html.Small(f"報告者: {report['reporter_username']} | 日時: {report['report_date']}"),
                    dbc.Card(dbc.CardBody(report['description']), className="mt-2 mb-3 bg-light")
                ])
                # is_open, title, body, is_open_admin, admin_details, editing_id, status, message
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
                # is_open, title, body, is_open_admin, admin_details, editing_id, status, message
                return True, report['title'], body, False, no_update, no_update, no_update, no_update

        # その他の予期せぬトリガー
        print("Unhandled trigger, preventing update.")
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
            return "", False, False
        else:
            return dbc.Alert(f"エラー: {msg}", color="danger"), True, True

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
            if triggered_id_str.startswith('{'):
                 triggered_button_id = json.loads(triggered_id_str)
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