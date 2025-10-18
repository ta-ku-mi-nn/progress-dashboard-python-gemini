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


    # ★★★★★★★★★★★★★★★★★★★★
    # ★★★ 修正箇所 ★★★
    # ★★★★★★★★★★★★★★★★★★★★
    @app.callback(
        # --- モーダルの Output (MATCH を使用) ---
        # どの report_type のモーダルを操作するかを MATCH で特定
        Output({'type': 'detail-modal', 'report_type': MATCH}, 'is_open'),
        Output({'type': 'detail-modal-title', 'report_type': MATCH}, 'children'),
        Output({'type': 'detail-modal-body', 'report_type': MATCH}, 'children'),
        Output({'type': 'admin-modal', 'report_type': MATCH}, 'is_open'),
        Output({'type': 'admin-detail-display', 'report_type': MATCH}, 'children'), # 管理者用詳細表示
        # --- Store の Output (MATCH を使用) ---
        # Stateを保持するStoreも MATCH で特定
        Output({'type': 'editing-id-store', 'report_type': MATCH}, 'data'),
        Output({'type': 'status-dropdown', 'report_type': MATCH}, 'value'),
        Output({'type': 'resolution-message-input', 'report_type': MATCH}, 'value'),
        # --- Input (トリガーとなる要素) ---
        # report-item のクリック (ALL で report_type ごとに監視)
        Input({'type': 'report-item', 'report_type': ALL, 'index': ALL}, 'n_clicks'),
        # 閉じる/キャンセルボタン (ALL で report_type ごとに監視)
        Input({'type': 'close-detail-modal', 'report_type': ALL}, 'n_clicks'),
        Input({'type': 'cancel-admin-modal', 'report_type': ALL}, 'n_clicks'),
        # --- State ---
        State('auth-store', 'data'),
        # prevent_initial_call=True # 初回読み込み時は実行しない
    )
    def handle_modal_toggle_v2(item_clicks, close_detail_clicks, cancel_admin_clicks, user_info):
        ctx = callback_context

        # トリガーとなった Input の ID ('prop_id') を取得
        # 例: '{"index":5,"report_type":"bug","type":"report-item"}.n_clicks'
        # 例: '{"report_type":"bug","type":"close-detail-modal"}.n_clicks'
        triggered_prop_id_str = ctx.triggered_prop_ids.get('.')
        if not triggered_prop_id_str:
            raise PreventUpdate

        # トリガーIDを解析して辞書形式に戻す
        try:
            # ".n_clicks" を除去して JSON としてパース
            triggered_id_dict = json.loads(triggered_prop_id_str.split('.')[0])
        except json.JSONDecodeError:
            print(f"Error parsing triggered_id: {triggered_prop_id_str}")
            raise PreventUpdate

        # トリガーの種類 (type) と report_type を取得
        trigger_type = triggered_id_dict.get('type')
        report_type = triggered_id_dict.get('report_type')

        print(f"Triggered type: {trigger_type}, Report type: {report_type}") # デバッグ用

        # --- モーダルを閉じる処理 ---
        if trigger_type in ['close-detail-modal', 'cancel-admin-modal']:
            print(f"Closing modal: {report_type} - {trigger_type}")
            # 対応する report_type のモーダルのみ is_open=False を返す
            # 他の Output は no_update
            if report_type == ctx.outputs_list[0][0]['id']['report_type']: # OutputのMATCHと比較
                return False, no_update, no_update, False, no_update, no_update, no_update, no_update
            else:
                 raise PreventUpdate # 異なる report_type のコールバックは無視

        # --- リスト項目クリック時の処理 ---
        if trigger_type == 'report-item':
            # クリックイベントの値 (n_clicks) を取得
            clicked_n_clicks = ctx.triggered[0]['value'] if ctx.triggered else None

            # n_clicks が None や 0 の場合はモーダルを開かない（または閉じる）
            if not clicked_n_clicks:
                print("Click value is None or 0, preventing modal open/closing.")
                # すべてのOutputに対して no_update を返すことで、現在の状態を維持
                # (もし開いていれば開いたまま、閉じていれば閉じたまま)
                # return [no_update] * 8
                # または、確実に閉じる場合は False を返す
                if report_type == ctx.outputs_list[0][0]['id']['report_type']:
                     return False, no_update, no_update, False, no_update, no_update, no_update, no_update
                else:
                    raise PreventUpdate

            # クリックされた report_id と report_type を取得
            report_id = triggered_id_dict.get('index')
            report_type = triggered_id_dict.get('report_type') # 再取得 (MATCH と一致するはず)

            # report_type が Output の MATCH と一致しない場合は無視
            if report_type != ctx.outputs_list[0][0]['id']['report_type']:
                raise PreventUpdate

            print(f"Item clicked: report_id={report_id}, report_type={report_type}")

            # データを取得
            get_func = get_all_bug_reports if report_type == 'bug' else get_all_feature_requests
            reports = get_func()
            report = next((r for r in reports if r['id'] == report_id), None)

            if not report:
                print("Report not found.")
                # エラー表示（例として detail-modal に表示）
                return True, "エラー", dbc.Alert("報告が見つかりません。", color="danger"), False, no_update, no_update, no_update, no_update

            is_admin = user_info and user_info.get('role') == 'admin'

            # --- ユーザーロールに応じて表示 ---
            if is_admin:
                print("Admin user - opening admin modal")
                # 管理者用モーダルを開く
                details = html.Div([
                    html.H5(report['title']),
                    html.Small(f"報告者: {report['reporter_username']} | 日時: {report['report_date']}"),
                    dbc.Card(dbc.CardBody(report['description']), className="mt-2 mb-3 bg-light")
                ])
                # is_open=True, title, body, is_open_admin=True, admin_details, editing_id, status, message
                return False, no_update, no_update, True, details, report_id, report['status'], report.get('resolution_message', '')
            else:
                print("Non-admin user - opening detail modal")
                # 詳細モーダルを開く
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
                # is_open=True, title, body, is_open_admin=False, admin_details, editing_id, status, message
                return True, report['title'], body, False, no_update, no_update, no_update, no_update

        # その他のトリガーの場合は更新しない
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
         State({'type': 'save-status-btn', 'report_type': MATCH}, 'id')], # ボタン自体のIDを取得して report_type を特定
        prevent_initial_call=True
    )
    def save_status_matched(n_clicks, bug_id, status, message, button_id):
        if not n_clicks or not bug_id:
            raise PreventUpdate

        # ボタンのIDから report_type を取得
        report_type = button_id['report_type']

        resolve_func = resolve_bug if report_type == 'bug' else resolve_request
        update_func = update_bug_status if report_type == 'bug' else update_request_status

        if status in ['対応済', '見送り']:
            success, msg = resolve_func(bug_id, message, status)
        elif status in ['未対応', '対応中']:
             # 対応メッセージはステータス更新時にはクリア（もしくはそのまま保持）するか、別途UIで制御する
             # ここでは resolve_func ではないので message は無視
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
    # (変更なし)
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
        triggered_prop_id_str = ctx.triggered_prop_ids.get('.') # Get the full property ID string
        if not triggered_prop_id_str:
            raise PreventUpdate

        # Parse the component ID part of the string
        try:
            triggered_id_str = triggered_prop_id_str.split('.')[0]
            # Check if it starts with '{' to ensure it's likely a JSON string
            if triggered_id_str.startswith('{'):
                 triggered_button_id = json.loads(triggered_id_str)
            else:
                 # Handle cases where the ID might not be JSON (shouldn't happen with pattern matching)
                 print(f"Warning: Triggered ID is not a JSON string: {triggered_id_str}")
                 raise PreventUpdate
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Error parsing triggered ID: {e}, ID string: {triggered_prop_id_str}")
            raise PreventUpdate # Should not happen if IDs are correct

        # Find the index corresponding to the triggered button
        triggered_index = -1
        for i, btn_id in enumerate(button_id_list):
            # Compare the dictionary IDs directly
            if btn_id == triggered_button_id:
                triggered_index = i
                break

        # Check if the click actually happened (n_clicks > 0 and not None)
        # ctx.triggered gives [{'prop_id': '...', 'value': n_clicks}, ...]
        if triggered_index == -1 or not ctx.triggered or ctx.triggered[0].get('value') is None:
             raise PreventUpdate # Click not found or n_clicks is None/0

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
             # Here, we only update the status. Message is ignored unless resolving.
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
            # toast_data for error? Could be useful.
            error_toast_data = {'timestamp': datetime.now().isoformat(), 'message': f"更新失敗: {msg}", 'source': f'{report_type}_report_error'}
            # return error_toast_data, no_update # Optionally show error toast
            return no_update, no_update # Or show nothing on failure here

    # --- IDを汎用化するためのヘルパー ---
    # (不要になったため削除)