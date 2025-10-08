# callbacks/homework_callbacks.py

import json
from dash import Input, Output, State, html, callback_context, no_update, ALL
import dash_bootstrap_components as dbc
from datetime import datetime

from data.nested_json_processor import (
    get_student_homework,
    add_homework,
    update_homework,
    update_homework_status,
    delete_homework
)

# --- ★★★ ここから全面的に修正 ★★★ ---

def register_homework_callbacks(app):
    """宿題管理に関連するコールバックを登録します。"""

    # --- 「宿題を追加」ボタンの有効/無効化 ---
    @app.callback(
        Output('add-homework-btn', 'disabled'),
        Input('student-dropdown', 'value'),
        prevent_initial_call=True
    )
    def toggle_add_homework_button(selected_student):
        return not selected_student

    # --- 宿題リストの表示 ---
    @app.callback(
        Output('homework-list-container', 'children'),
        [Input('student-dropdown', 'value'),
         Input('admin-update-trigger', 'data')], # 保存・削除成功時に再描画
        State('school-dropdown', 'value')
    )
    def update_homework_list(selected_student, update_trigger, selected_school):
        if not selected_student or not selected_school:
            return dbc.Alert("生徒を選択すると宿題が表示されます。", color="info")

        homework_list = get_student_homework(selected_school, selected_student)

        if not homework_list:
            return dbc.Alert("この生徒には宿題がありません。", color="secondary", className="mt-3")

        cards = []
        status_colors = {"完了": "success", "進行中": "primary", "未着手": "warning"}
        
        # グループ化された宿題を追跡
        processed_groups = set()

        for hw in homework_list:
            if hw['task_group_id'] and hw['task_group_id'] in processed_groups:
                continue

            # グループタスクの場合
            if hw['task_group_id']:
                group_tasks = [t for t in homework_list if t['task_group_id'] == hw['task_group_id']]
                processed_groups.add(hw['task_group_id'])
                
                start = min(t['task_date'] for t in group_tasks)
                end = max(t['task_date'] for t in group_tasks)
                
                header = dbc.CardHeader([
                    html.H5(hw['task'], className="mb-0 d-inline-block"),
                    dbc.Badge(f"{hw['subject']}", color="info", className="ms-2")
                ])
                
                body_items = [
                    dbc.ListGroupItem([
                        dbc.Row([
                            dbc.Col(f"{t['task_date']}", width=4),
                            dbc.Col(dbc.Select(
                                id={'type': 'homework-status-select', 'id': t['id']},
                                options=[{"label": s, "value": s} for s in ["未着手", "進行中", "完了"]],
                                value=t['status'], size="sm"
                            ), width=8),
                        ], align="center")
                    ]) for t in sorted(group_tasks, key=lambda x: x['task_date'])
                ]

                footer = dbc.CardFooter([
                    html.Small(f"期間: {start} ~ {end}", className="text-muted"),
                    dbc.Button(
                        "グループごと削除", 
                        id={'type': 'delete-homework-group-btn', 'group_id': hw['task_group_id']},
                        color="danger", size="sm", outline=True, className="float-end"
                    )
                ])

                cards.append(dbc.Card([header, dbc.ListGroup(body_items, flush=True), footer], className="mb-3"))

            # 個別タスクの場合
            else:
                card = dbc.Card([
                    dbc.CardBody([
                        html.H5(hw['task'], className="card-title"),
                        html.H6(f"科目: {hw['subject']}", className="card-subtitle mb-2 text-muted"),
                        html.P(f"期限: {hw['task_date']}", className="card-text"),
                        dbc.Select(
                            id={'type': 'homework-status-select', 'id': hw['id']},
                            options=[{"label": s, "value": s} for s in ["未着手", "進行中", "完了"]],
                            value=hw['status'], size="sm", className="mb-2"
                        ),
                        dbc.Button("編集", id={'type': 'edit-homework-btn', 'id': hw['id']}, color="secondary", size="sm", outline=True, className="me-2"),
                        dbc.Button("削除", id={'type': 'delete-homework-btn', 'id': hw['id']}, color="danger", size="sm", outline=True)
                    ])
                ], color=status_colors.get(hw['status'], "light"), inverse=(hw['status'] != '未着手'), class_name="mb-3")
                cards.append(card)

        return cards

    # --- 宿題追加/編集モーダルの開閉・データ設定 ---
    @app.callback(
        [Output('homework-modal', 'is_open'),
         Output('homework-modal-title', 'children'),
         Output('editing-homework-id-store', 'data'),
         Output('homework-subject', 'value'),
         Output('homework-task', 'value'),
         Output('homework-date-picker', 'start_date'),
         Output('homework-date-picker', 'end_date'),
         Output('homework-date-picker', 'disabled')],
        [Input('add-homework-btn', 'n_clicks'),
         Input({'type': 'edit-homework-btn', 'id': ALL}, 'n_clicks')],
        [State('student-dropdown', 'value'), State('school-dropdown', 'value')],
        prevent_initial_call=True
    )
    def open_homework_modal(add_clicks, edit_clicks, student, school):
        ctx = callback_context
        if not ctx.triggered or not (add_clicks or any(edit_clicks)):
            return no_update

        trigger_id = ctx.triggered_id
        
        if trigger_id == 'add-homework-btn':
            return True, "宿題の追加", None, None, "", None, None, False

        if isinstance(trigger_id, dict) and trigger_id['type'] == 'edit-homework-btn':
            homework_id = trigger_id['id']
            homework_list = get_student_homework(school, student)
            hw_to_edit = next((hw for hw in homework_list if hw['id'] == homework_id), None)
            if hw_to_edit:
                date = datetime.strptime(hw_to_edit['task_date'], '%Y-%m-%d').date()
                return True, "宿題の編集", homework_id, hw_to_edit['subject'], hw_to_edit['task'], date, date, True
        
        return [no_update] * 8
    
    # --- 宿題の保存（新規・更新） ---
    @app.callback(
        [Output('homework-alert', 'children'),
         Output('homework-alert', 'is_open'),
         Output('admin-update-trigger', 'data', allow_duplicate=True),
         Output('homework-modal', 'is_open', allow_duplicate=True)],
        Input('save-homework-button', 'n_clicks'),
        [State('editing-homework-id-store', 'data'),
         State('school-dropdown', 'value'),
         State('student-dropdown', 'value'),
         State('homework-subject', 'value'),
         State('homework-task', 'value'),
         State('homework-date-picker', 'start_date'),
         State('homework-date-picker', 'end_date')],
        prevent_initial_call=True
    )
    def save_homework(n_clicks, homework_id, school, student, subject, task, start_date, end_date):
        if not n_clicks:
            return "", False, no_update, no_update

        if not all([school, student, subject, task, start_date]):
            return dbc.Alert("科目、課題内容、開始日を入力してください。", color="danger"), True, no_update, no_update

        # 更新の場合
        if homework_id:
            success, message = update_homework(homework_id, subject, task, start_date)
        # 新規作成の場合
        else:
            if not end_date: # 終了日がなければ開始日と同じにする
                end_date = start_date
            success, message = add_homework(school, student, subject, task, start_date, end_date)
        
        if success:
            return "", False, datetime.now().timestamp(), False
        else:
            return dbc.Alert(message, color="danger"), True, no_update, no_update

    # --- 宿題の削除（個別・グループ）とステータス更新 ---
    @app.callback(
        Output('admin-update-trigger', 'data', allow_duplicate=True),
        [Input({'type': 'delete-homework-btn', 'id': ALL}, 'n_clicks'),
         Input({'type': 'delete-homework-group-btn', 'group_id': ALL}, 'n_clicks'),
         Input({'type': 'homework-status-select', 'id': ALL}, 'value')],
        prevent_initial_call=True
    )
    def handle_homework_actions(delete_clicks, delete_group_clicks, status_values):
        ctx = callback_context
        if not ctx.triggered:
            return no_update

        trigger_id = ctx.triggered_id
        
        # 個別削除
        if 'delete-homework-btn' in trigger_id.get('type', ''):
            if not ctx.triggered[0]['value']: return no_update
            homework_id = trigger_id['id']
            delete_homework(homework_id=homework_id)
            return datetime.now().timestamp()
            
        # グループ削除
        if 'delete-homework-group-btn' in trigger_id.get('type', ''):
            if not ctx.triggered[0]['value']: return no_update
            group_id = trigger_id['group_id']
            delete_homework(task_group_id=group_id)
            return datetime.now().timestamp()
        
        # ステータス更新
        if 'homework-status-select' in trigger_id.get('type', ''):
            homework_id = trigger_id['id']
            new_status = ctx.triggered[0]['value']
            update_homework_status(homework_id, new_status)
            return no_update # ステータス更新ではリスト全体の再描画は不要

        return no_update
    
        # --- 宿題ステータスの更新 ---
    @app.callback(
        [Output('success-toast', 'header', allow_duplicate=True),
         Output('success-toast', 'is_open', allow_duplicate=True)], # ★ is_open をOutputに追加
        Input({'type': 'homework-status-select', 'id': ALL}, 'value'),
        prevent_initial_call=True
    )
    def update_status(values):
        ctx = callback_context
        if not ctx.triggered or not ctx.triggered[0]['value']:
            return no_update, no_update

        trigger_prop_id = ctx.triggered[0]['prop_id']
        trigger_id_str = trigger_prop_id.split('.')[0]
        hw_id = json.loads(trigger_id_str)['id']
        new_status = ctx.triggered[0]['value']
        
        update_homework_status(hw_id, new_status)
        # ★ headerとis_openの両方を返す
        return f"宿題ステータスを「{new_status}」に更新しました。", True

    # --- モーダルを閉じる ---
    @app.callback(
        Output('homework-modal', 'is_open', allow_duplicate=True),
        Input('close-homework-modal', 'n_clicks'),
        prevent_initial_call=True
    )
    def close_homework_modal(n_clicks):
        if n_clicks:
            return False
        return no_update