"""
宿題管理機能に関連するコールバックを定義します。
"""
import json
import dash
from dash import Input, Output, State, html, callback_context, no_update
import dash_bootstrap_components as dbc

# データベース操作用のヘルパー関数をインポート
from data.nested_json_processor import (
    get_student_homework,
    add_homework,
    update_homework_status,
    delete_homework
)

def register_homework_callbacks(app):
    """
    宿題管理に関連するコールバックを登録します。

    Args:
        app (dash.Dash): Dashアプリケーションインスタンス。
    """

    # --- 宿題リストの表示 ---
    @app.callback(
        Output('homework-list-container', 'children'),
        Input('student-dropdown', 'value'),
        State('school-dropdown', 'value')
    )
    def update_homework_list(selected_student, selected_school):
        if not selected_student or not selected_school:
            return dbc.Alert("生徒を選択すると宿題が表示されます。", color="info")

        homework_list = get_student_homework(selected_school, selected_student)

        if not homework_list:
            return dbc.Alert("この生徒には宿題がありません。", color="secondary")

        cards = []
        status_colors = {
            "完了": "success",
            "進行中": "primary",
            "未着手": "warning"
        }
        for hw in homework_list:
            card = dbc.Card([
                dbc.CardBody([
                    html.H5(hw['task'], className="card-title"),
                    html.H6(f"科目: {hw['subject']}", className="card-subtitle mb-2 text-muted"),
                    html.P(f"提出期限: {hw['due_date']}", className="card-text"),
                    dbc.Select(
                        id={'type': 'homework-status-select', 'id': hw['id']},
                        options=[
                            {"label": "未着手", "value": "未着手"},
                            {"label": "進行中", "value": "進行中"},
                            {"label": "完了", "value": "完了"},
                        ],
                        value=hw['status'],
                        size="sm",
                        className="mb-2"
                    ),
                    dbc.Button("削除", id={'type': 'delete-homework-btn', 'id': hw['id']},
                               color="danger", size="sm", outline=True)
                ])
            ], color=status_colors.get(hw['status'], "light"), inverse=(hw['status'] != '未着手'),
               class_name="mb-3")
            cards.append(card)

        return cards

    # --- 宿題追加モーダルの開閉 ---
    @app.callback(
        Output('homework-modal', 'is_open'),
        [Input('add-homework-btn', 'n_clicks'),
         Input('close-homework-modal', 'n_clicks'),
         Input('save-homework-button', 'n_clicks')],
        State('homework-modal', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_homework_modal(add_clicks, close_clicks, save_clicks, is_open):
        ctx = callback_context
        if not ctx.triggered:
            return is_open
        
        # どのボタンが押されたかに関わらず、モーダルを閉じる
        return not is_open

    # --- 新規宿題の保存 ---
    @app.callback(
        [Output('homework-alert', 'children', allow_duplicate=True),
         Output('student-dropdown', 'value', allow_duplicate=True)], # リスト再描画のトリガー
        Input('save-homework-button', 'n_clicks'),
        [State('school-dropdown', 'value'),
         State('student-dropdown', 'value'),
         State('homework-subject', 'value'),
         State('homework-task', 'value'),
         State('homework-due-date', 'date')],
        prevent_initial_call=True
    )
    def save_new_homework(n_clicks, school, student, subject, task, due_date):
        if not n_clicks:
            return no_update, no_update

        if not all([school, student, subject, task, due_date]):
            return dbc.Alert("すべての項目を入力してください。", color="danger"), no_update

        success, message = add_homework(school, student, subject, task, due_date)

        if success:
            # 成功した場合、 student-dropdown の値を更新して宿題リストを再描画させる
            return no_update, student
        
        return dbc.Alert(message, color="danger"), no_update

    # --- 宿題ステータスの更新 ---
    @app.callback(
        Output('success-toast', 'header', allow_duplicate=True),
        Input({'type': 'homework-status-select', 'id': dash.ALL}, 'value'),
        prevent_initial_call=True
    )
    def update_status(values):
        ctx = callback_context
        if not ctx.triggered or not ctx.triggered[0]['value']:
            return no_update

        trigger_prop_id = ctx.triggered[0]['prop_id']
        trigger_id_str = trigger_prop_id.split('.')[0]
        hw_id = json.loads(trigger_id_str)['id']
        new_status = ctx.triggered[0]['value']
        
        update_homework_status(hw_id, new_status)
        return f"宿題ステータスを「{new_status}」に更新しました。"
    
    # --- 宿題の削除 ---
    @app.callback(
        Output('student-dropdown', 'value', allow_duplicate=True), # リスト再描画のトリガー
        Input({'type': 'delete-homework-btn', 'id': dash.ALL}, 'n_clicks'),
        State('student-dropdown', 'value'),
        prevent_initial_call=True
    )
    def delete_homework_item(n_clicks, student_name):
        # n_clicksは各ボタンのクリック回数のリスト。[None, 1, None] のようになる
        if not any(n_clicks):
            return no_update

        ctx = callback_context
        trigger_prop_id = ctx.triggered[0]['prop_id']
        trigger_id_str = trigger_prop_id.split('.')[0]
        hw_id = json.loads(trigger_id_str)['id']
        
        delete_homework(hw_id)
        
        # 削除後に宿題リストを再描画するため、student-dropdownの値を強制的に更新する
        return student_name