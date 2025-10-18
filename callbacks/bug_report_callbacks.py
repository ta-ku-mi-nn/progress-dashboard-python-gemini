# callbacks/bug_report_callbacks.py

from dash import Input, Output, State, html, no_update, callback_context, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime

from data.nested_json_processor import (
    add_bug_report, get_all_bug_reports, update_bug_status, resolve_bug
)

def register_bug_report_callbacks(app):
    """不具合報告ページのコールバックを登録する"""

    # --- 不具合報告の送信 ---
    @app.callback(
        [Output('bug-report-alert', 'children'),
         Output('bug-report-alert', 'is_open'),
         Output('bug-report-title', 'value'),
         Output('bug-report-description', 'value'),
         Output('toast-trigger', 'data', allow_duplicate=True)],
        Input('submit-bug-report-btn', 'n_clicks'),
        [State('auth-store', 'data'),
         State('bug-report-title', 'value'),
         State('bug-report-description', 'value')],
        prevent_initial_call=True
    )
    def submit_bug_report(n_clicks, user_info, title, description):
        if not n_clicks:
            raise PreventUpdate

        if not user_info or not user_info.get('username'):
            return dbc.Alert("ログインしていません。", color="danger"), True, no_update, no_update, no_update

        if not title or not description:
            return dbc.Alert("件名と詳細を入力してください。", color="warning"), True, no_update, no_update, no_update

        reporter = user_info['username']
        success, message = add_bug_report(reporter, title, description)

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'bug_report'}
            return "", False, "", "", toast_data
        else:
            return dbc.Alert(f"エラー: {message}", color="danger"), True, no_update, no_update, no_update

    # --- 不具合一覧の表示 ---
    @app.callback(
        Output('bug-report-list-container', 'children'),
        [Input('url', 'pathname'),
         Input('toast-trigger', 'data')]
    )
    def update_bug_report_list(pathname, toast_data):
        ctx = callback_context
        if ctx.triggered_id == 'toast-trigger' and (not toast_data or toast_data.get('source') != 'bug_report'):
            raise PreventUpdate

        if pathname != '/bug-report':
            raise PreventUpdate

        reports = get_all_bug_reports()
        if not reports:
            return dbc.Alert("報告されている不具合はありません。", color="info")

        def get_status_color(status):
            if status == '対応済': return "success"
            if status == '対応中': return "warning"
            return "secondary"

        items = [
            dbc.ListGroupItem(
                dbc.Row([
                    dbc.Col(f"[{r['report_date']}] {r['title']}", width=8),
                    dbc.Col(r['reporter_username'], width=2),
                    dbc.Col(dbc.Badge(r['status'], color=get_status_color(r['status'])), width=2),
                ], align="center"),
                id={'type': 'bug-report-item', 'index': r['id']},
                action=True,
                className="bug-list-item"
            ) for r in reports
        ]
        return dbc.ListGroup(items, flush=True)

    # --- 詳細モーダル（一般ユーザー向け）の表示 ---
    @app.callback(
        [Output('bug-detail-modal', 'is_open'),
         Output('bug-detail-modal-title', 'children'),
         Output('bug-detail-modal-body', 'children')],
        [Input({'type': 'bug-report-item', 'index': ALL}, 'n_clicks'),
         Input('close-bug-detail-modal', 'n_clicks')],
        [State('auth-store', 'data')],
        prevent_initial_call=True
    )
    def toggle_bug_detail_modal(item_clicks, close_clicks, user_info):
        ctx = callback_context

        # 起動条件を厳格化
        if not ctx.triggered_id or (isinstance(ctx.triggered_id, dict) and not any(item_clicks)):
            if not (ctx.triggered_id == 'close-bug-detail-modal' and close_clicks):
                 raise PreventUpdate

        # ユーザーが管理者ならこのコールバックは動作しない
        if user_info and user_info.get('role') == 'admin':
            raise PreventUpdate

        trigger_id = ctx.triggered_id

        if trigger_id == 'close-bug-detail-modal':
            return False, no_update, no_update

        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'bug-report-item':
            bug_id = trigger_id['index']
            reports = get_all_bug_reports()
            report = next((r for r in reports if r['id'] == bug_id), None)

            if not report:
                return False, "エラー", "報告が見つかりません。"

            body = [
                html.P([html.Strong("報告者: "), report['reporter_username']]),
                html.P([html.Strong("報告日時: "), report['report_date']]),
                html.Hr(),
                html.P(report['description'], style={'whiteSpace': 'pre-wrap'}),
            ]

            if report['status'] == '対応済' and report['resolution_message']:
                body.extend([
                    html.Hr(),
                    html.Strong("対応内容:"),
                    dbc.Card(dbc.CardBody(report['resolution_message']), className="mt-2 bg-light")
                ])

            return True, report['title'], body

        return no_update, no_update, no_update

    # --- 管理者向け編集モーダルの表示 ---
    @app.callback(
        [Output('bug-admin-modal', 'is_open'),
         Output('editing-bug-id-store', 'data'),
         Output('bug-status-dropdown', 'value'),
         Output('bug-resolution-message-input', 'value'),
         Output('bug-admin-detail-display', 'children')],
        [Input({'type': 'bug-report-item', 'index': ALL}, 'n_clicks'),
         Input('cancel-bug-admin-modal', 'n_clicks')],
        [State('auth-store', 'data')],
        prevent_initial_call=True
    )
    def toggle_admin_modal(edit_clicks, cancel_clicks, user_info):
        ctx = callback_context

        # 起動条件を厳格化
        if not ctx.triggered_id or (isinstance(ctx.triggered_id, dict) and not any(edit_clicks)):
            if not (ctx.triggered_id == 'cancel-bug-admin-modal' and cancel_clicks):
                raise PreventUpdate

        # ユーザーが管理者でなければこのコールバックは動作しない
        if not user_info or user_info.get('role') != 'admin':
            raise PreventUpdate

        trigger_id = ctx.triggered_id

        if trigger_id == 'cancel-bug-admin-modal':
            return False, None, no_update, no_update, None

        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'bug-report-item':
            bug_id = trigger_id['index']
            reports = get_all_bug_reports()
            report = next((r for r in reports if r['id'] == bug_id), None)
            if report:
                # 詳細表示コンポーネントを作成
                details = html.Div([
                    html.H5(report['title']),
                    html.Small(f"報告者: {report['reporter_username']} | 日時: {report['report_date']}"),
                    dbc.Card(dbc.CardBody(report['description']), className="mt-2 mb-3 bg-light")
                ])
                return True, bug_id, report['status'], report.get('resolution_message', ''), details

        return no_update, no_update, no_update, no_update, None

    # --- 管理者によるステータス更新 ---
    @app.callback(
        [Output('bug-admin-alert', 'children'),
         Output('bug-admin-alert', 'is_open'),
         Output('toast-trigger', 'data', allow_duplicate=True),
         Output('bug-admin-modal', 'is_open', allow_duplicate=True)],
        Input('save-bug-status-btn', 'n_clicks'),
        [State('editing-bug-id-store', 'data'),
         State('bug-status-dropdown', 'value'),
         State('bug-resolution-message-input', 'value')],
        prevent_initial_call=True
    )
    def save_bug_status(n_clicks, bug_id, status, message):
        if not n_clicks or not bug_id:
            raise PreventUpdate

        if status == '対応済':
            success, msg = resolve_bug(bug_id, message)
        else:
            success, msg = update_bug_status(bug_id, status)

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': msg, 'source': 'bug_report'}
            return "", False, toast_data, False
        else:
            return dbc.Alert(f"エラー: {msg}", color="danger"), True, no_update, no_update
