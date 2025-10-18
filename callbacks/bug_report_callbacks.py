# callbacks/bug_report_callbacks.py

from dash import Input, Output, State, html, no_update, callback_context, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime

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

    # --- 詳細モーダル表示 (共通化) ---
    @app.callback(
        [Output({'type': 'detail-modal', 'report_type': MATCH}, 'is_open'),
         Output({'type': 'detail-modal-title', 'report_type': MATCH}, 'children'),
         Output({'type': 'detail-modal-body', 'report_type': MATCH}, 'children')],
        [Input({'type': 'report-item', 'report_type': MATCH, 'index': ALL}, 'n_clicks'),
         Input({'type': 'close-detail-modal', 'report_type': MATCH}, 'n_clicks')],
        [State('auth-store', 'data'),
         State({'type': 'report-item', 'report_type': MATCH, 'index': ALL}, 'id')],
        prevent_initial_call=True
    )
    def toggle_detail_modal(item_clicks, close_clicks, user_info, item_ids):
        ctx = callback_context
        if not ctx.triggered_id or not any(item_clicks + [close_clicks]):
             raise PreventUpdate

        # クリックされたボタンの report_type を取得
        triggered_prop_id = ctx.triggered_prop_ids.get('.')
        if not triggered_prop_id: raise PreventUpdate # トリガーIDがなければ中断

        try:
             # Input IDが辞書形式の場合
             triggered_id_dict = json.loads(triggered_prop_id.split('.')[0])
             report_type = triggered_id_dict.get('report_type')
        except (json.JSONDecodeError, AttributeError):
             # Input IDが単純な文字列の場合 (closeボタンなど)
             # この書き方だと report_type が取れないので工夫が必要
             # closeボタンのIDに type と report_type を含めるように変更
              if triggered_prop_id.startswith('close-'):
                  report_type = triggered_prop_id.split('-')[1] # e.g., "close-bug-detail-modal" -> "bug"
              else:
                   raise PreventUpdate


        # 管理者の場合は管理者モーダルを開くため、このコールバックは動作させない
        if user_info and user_info.get('role') == 'admin':
            raise PreventUpdate

        # Closeボタンが押された場合
        if isinstance(ctx.triggered_id, str) and ctx.triggered_id.startswith('close-'):
             return False, no_update, no_update

        # report-item がクリックされた場合
        if isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get('type') == 'report-item':
            bug_id = ctx.triggered_id['index']
            get_func = get_all_bug_reports if report_type == 'bug' else get_all_feature_requests
            reports = get_func()
            report = next((r for r in reports if r['id'] == bug_id), None)

            if not report:
                return False, "エラー", "報告が見つかりません。"

            body = [
                html.P([html.Strong("報告者: "), report['reporter_username']]),
                html.P([html.Strong("報告日時: "), report['report_date']]),
                html.Hr(),
                html.P(report['description'], style={'whiteSpace': 'pre-wrap'}),
            ]

            if report['status'] in ['対応済', '見送り'] and report['resolution_message']:
                status_label = "対応内容" if report['status'] == '対応済' else "コメント"
                body.extend([
                    html.Hr(),
                    html.Strong(f"{status_label}:"),
                    dbc.Card(dbc.CardBody(report['resolution_message']), className="mt-2 bg-light")
                ])

            return True, report['title'], body

        return no_update, no_update, no_update


    # --- 管理者向け編集モーダル表示 (共通化) ---
    @app.callback(
        [Output({'type': 'admin-modal', 'report_type': MATCH}, 'is_open'),
         Output({'type': 'editing-id-store', 'report_type': MATCH}, 'data'),
         Output({'type': 'status-dropdown', 'report_type': MATCH}, 'value'),
         Output({'type': 'resolution-message-input', 'report_type': MATCH}, 'value'),
         Output({'type': 'admin-detail-display', 'report_type': MATCH}, 'children')],
        [Input({'type': 'report-item', 'report_type': MATCH, 'index': ALL}, 'n_clicks'),
         Input({'type': 'cancel-admin-modal', 'report_type': MATCH}, 'n_clicks')],
        [State('auth-store', 'data'),
         State({'type': 'report-item', 'report_type': MATCH, 'index': ALL}, 'id')],
        prevent_initial_call=True
    )
    def toggle_admin_modal(edit_clicks, cancel_clicks, user_info, item_ids):
        ctx = callback_context
        if not ctx.triggered_id or not any(edit_clicks + [cancel_clicks]):
            raise PreventUpdate

        triggered_prop_id = ctx.triggered_prop_ids.get('.')
        if not triggered_prop_id: raise PreventUpdate

        try:
             triggered_id_dict = json.loads(triggered_prop_id.split('.')[0])
             report_type = triggered_id_dict.get('report_type')
        except (json.JSONDecodeError, AttributeError):
             if triggered_prop_id.startswith('cancel-'):
                 report_type = triggered_prop_id.split('-')[1]
             else:
                  raise PreventUpdate

        # 管理者でなければこのコールバックは動作しない
        if not user_info or user_info.get('role') != 'admin':
            raise PreventUpdate

        # Cancelボタンが押された場合
        if isinstance(ctx.triggered_id, str) and ctx.triggered_id.startswith('cancel-'):
            return False, None, no_update, no_update, None

        # report-item がクリックされた場合
        if isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get('type') == 'report-item':
            bug_id = ctx.triggered_id['index']
            get_func = get_all_bug_reports if report_type == 'bug' else get_all_feature_requests
            reports = get_func()
            report = next((r for r in reports if r['id'] == bug_id), None)

            if report:
                details = html.Div([
                    html.H5(report['title']),
                    html.Small(f"報告者: {report['reporter_username']} | 日時: {report['report_date']}"),
                    dbc.Card(dbc.CardBody(report['description']), className="mt-2 mb-3 bg-light")
                ])
                return True, bug_id, report['status'], report.get('resolution_message', ''), details

        return no_update, no_update, no_update, no_update, None

    # --- 管理者によるステータス更新 (共通化) ---
    @app.callback(
        [Output({'type': 'admin-alert', 'report_type': MATCH}, 'children'),
         Output({'type': 'admin-alert', 'report_type': MATCH}, 'is_open'),
         Output('toast-trigger', 'data', allow_duplicate=True),
         Output({'type': 'admin-modal', 'report_type': MATCH}, 'is_open', allow_duplicate=True),
         Output('report-update-trigger', 'data', allow_duplicate=True)], # リスト更新トリガー
        Input({'type': 'save-status-btn', 'report_type': MATCH}, 'n_clicks'),
        [State({'type': 'editing-id-store', 'report_type': MATCH}, 'data'),
         State({'type': 'status-dropdown', 'report_type': MATCH}, 'value'),
         State({'type': 'resolution-message-input', 'report_type': MATCH}, 'value'),
         # report_type を State として取得
         State({'type': 'save-status-btn', 'report_type': MATCH}, 'id')],
        prevent_initial_call=True
    )
    def save_status(n_clicks, bug_id, status, message, button_id):
        if not n_clicks or not bug_id:
            raise PreventUpdate

        report_type = button_id['report_type'] # ボタンのIDから report_type を取得
        resolve_func = resolve_bug if report_type == 'bug' else resolve_request
        update_func = update_bug_status if report_type == 'bug' else update_request_status

        if status in ['対応済', '見送り']:
            success, msg = resolve_func(bug_id, message, status) # resolve関数にもstatusを渡すように変更が必要な場合
        else:
            success, msg = update_func(bug_id, status)

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': msg, 'source': f'{report_type}_report'}
            update_trigger = {'timestamp': datetime.now().isoformat(), 'type': report_type}
            # アラートはクリア、トースト表示、モーダル閉じる、リスト更新トリガー
            return "", False, toast_data, False, update_trigger
        else:
            # エラーアラート表示、トーストなし、モーダル開いたまま、リスト更新なし
            return dbc.Alert(f"エラー: {msg}", color="danger"), True, no_update, no_update, no_update

    # --- IDを汎用化するためのヘルパー ---
    # (既存のコールバック内で直接MATCHを使用するため、このセクションは不要)