# callbacks/homework_callbacks.py

from dash import Input, Output, State, dcc, html, no_update, callback_context, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from datetime import date, timedelta, datetime
import json
import pandas as pd

from data.nested_json_processor import (
    get_all_subjects, get_all_master_textbooks, get_all_homework_for_student,
    get_homework_for_textbook, add_or_update_homework, delete_homework_group
)

def register_homework_callbacks(app):
    """宿題管理ページのコールバックを登録します。"""

    # 宿題リストの更新コールバック（変更なし）
    @app.callback(
        Output('homework-list-container', 'children'),
        [Input('student-selection-store', 'data'),
         Input('homework-modal', 'is_open')]
    )
    def update_homework_list(student_id, modal_is_open):
        ctx = callback_context
        if ctx.triggered_id == 'homework-modal' and modal_is_open:
            raise PreventUpdate
        if not student_id:
            return dbc.Alert("まずホーム画面で生徒を選択してください。", color="info", className="mt-4")
        all_homework = get_all_homework_for_student(student_id)
        if not all_homework:
            return dbc.Alert("この生徒の宿題はまだ登録されていません。「新しい宿題を追加」から作成できます。", color="info", className="mt-4")
        df = pd.DataFrame(all_homework)
        grouped = df.groupby(['master_textbook_id', 'custom_textbook_name', 'textbook_name', 'subject'])
        cards = []
        for (textbook_id, custom_name, textbook_name, subject), group in grouped:
            group = group.sort_values('task_date')
            preview_items = []
            for _, row in group.head(3).iterrows():
                try:
                    dt = pd.to_datetime(row['task_date']).strftime('%m/%d')
                    preview_items.append(html.Span(f"{dt}: {row['task'] or ''}", className="d-block small text-muted"))
                except (ValueError, TypeError):
                     preview_items.append(html.Span(f"日付不明: {row['task'] or ''}", className="d-block small text-muted"))
            card_content = [
                html.H5(textbook_name or "名称未設定", className="card-title"),
                html.H6(subject or "科目未設定", className="card-subtitle text-muted mb-2 small"),
                html.Div(preview_items),
            ]
            edit_id = {
                'type': 'edit-homework-btn',
                'textbook_id': int(textbook_id) if pd.notna(textbook_id) else -1,
                'custom_name': custom_name if pd.notna(custom_name) else ''
            }
            cards.append(
                dbc.Col(dbc.Card([
                    dbc.CardBody(card_content),
                    dbc.CardFooter(dbc.Button("編集", id=edit_id, color="secondary", outline=True, size="sm")),
                ], className="h-100 subject-card-hover"), width=12, md=6, lg=4, className="mb-4")
            )
        return dbc.Row(cards)

    # モーダル開閉コールバック（変更なし）
    @app.callback(
        [Output('homework-modal', 'is_open'),
         Output('homework-modal-title', 'children'),
         Output('editing-homework-store', 'data'),
         Output('homework-modal-alert', 'is_open', allow_duplicate=True)],
        [Input('add-homework-btn', 'n_clicks'),
         Input({'type': 'edit-homework-btn', 'textbook_id': ALL, 'custom_name': ALL}, 'n_clicks'),
         Input('cancel-homework-btn', 'n_clicks')],
        [State('homework-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_homework_modal(add_clicks, edit_clicks, cancel_clicks, is_open):
        ctx = callback_context
        if not ctx.triggered or (isinstance(ctx.triggered_id, dict) and not ctx.triggered[0]['value']):
            raise PreventUpdate
        trigger_id = ctx.triggered_id
        if trigger_id == 'cancel-homework-btn':
            return False, no_update, {}, False
        if trigger_id == 'add-homework-btn':
            return True, "新しい宿題を追加", {'mode': 'new'}, False
        if isinstance(trigger_id, dict):
            return True, "宿題を編集", {'mode': 'edit', **trigger_id}, False
        return not is_open, no_update, {}, False

    # モーダルへのデータ読み込みコールバック（変更なし）
    @app.callback(
        [Output('homework-modal-subject-dropdown', 'value'),
         Output('homework-modal-textbook-dropdown', 'options'),
         Output('homework-modal-textbook-dropdown', 'value'),
         Output('homework-modal-custom-textbook-input', 'value'),
         Output({'type': 'homework-modal-range-input', 'index': ALL}, 'value'),
         Output('modal-remarks-input', 'value'),
         Output('modal-test-result-input', 'value'),
         Output('modal-achievement-input', 'value')],
        [Input('editing-homework-store', 'data')],
        [State('student-selection-store', 'data')],
        prevent_initial_call=True
    )
    def load_homework_into_modal(editing_data, student_id):
        if not editing_data:
            raise PreventUpdate
        if editing_data.get('mode') == 'new':
            return None, [], None, "", [''] * 7, "", "", None
        if not student_id or editing_data.get('mode') != 'edit':
             return None, [], None, "", [''] * 7, "", "", None
        textbook_id = editing_data.get('textbook_id', -1)
        custom_name = editing_data.get('custom_name', '')
        homework_list = get_homework_for_textbook(student_id, textbook_id if textbook_id != -1 else None, custom_name)
        output_values = [''] * 7; today = date.today()
        hw_dict = {hw['task_date']: hw['task'] for hw in homework_list}
        for i in range(7):
            current_date_str = (today + timedelta(days=i)).strftime('%Y-%m-%d')
            if current_date_str in hw_dict:
                output_values[i] = hw_dict[current_date_str]
        other_info = json.loads(homework_list[0]['other_info']) if homework_list and homework_list[0]['other_info'] else {}
        all_textbooks = get_all_master_textbooks()
        selected_book = next((b for b in all_textbooks if b['id'] == textbook_id), None)
        subject = selected_book['subject'] if selected_book else None
        options = []
        if subject:
            options = [{'label': b['book_name'], 'value': b['id']} for b in all_textbooks if b['subject'] == subject]
        return (
            subject, options, textbook_id if textbook_id != -1 else None, custom_name,
            output_values, other_info.get('remarks', ''), other_info.get('test_result', ''),
            other_info.get('achievement', None)
        )

    # 科目ドロップダウンの更新コールバック（変更なし）
    @app.callback(
        [Output('homework-modal-subject-dropdown', 'options'),
         Output('homework-modal-subject-dropdown', 'disabled')],
        Input('student-selection-store', 'data')
    )
    def update_modal_subject_dropdown(student_id):
        if not student_id:
            return [], True
        subjects = get_all_subjects()
        options = [{'label': s, 'value': s} for s in subjects]
        return options, False

    # 参考書ドロップダウンの更新コールバック（変更なし）
    @app.callback(
        [Output('homework-modal-textbook-dropdown', 'options', allow_duplicate=True),
         Output('homework-modal-textbook-dropdown', 'disabled')],
        Input('homework-modal-subject-dropdown', 'value'),
        prevent_initial_call=True
    )
    def update_modal_textbook_dropdown(subject):
        if not subject:
            return [], True
        all_textbooks = get_all_master_textbooks()
        subject_textbooks = [b for b in all_textbooks if b['subject'] == subject]
        options = [{'label': b['book_name'], 'value': b['id']} for b in subject_textbooks]
        return options, False

    # 保存コールバック（変更なし）
    @app.callback(
        [Output('homework-modal-alert', 'children'),
         Output('homework-modal-alert', 'is_open'),
         Output('homework-modal', 'is_open', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True)],
        Input('save-homework-modal-btn', 'n_clicks'),
        [State('student-selection-store', 'data'),
         State('homework-modal-subject-dropdown', 'value'),
         State('homework-modal-textbook-dropdown', 'value'),
         State('homework-modal-custom-textbook-input', 'value'),
         State({'type': 'homework-modal-range-input', 'index': ALL}, 'value'),
         State('modal-remarks-input', 'value'),
         State('modal-test-result-input', 'value'),
         State('modal-achievement-input', 'value')],
        prevent_initial_call=True
    )
    def save_homework_from_modal(n_clicks, student_id, subject, textbook_id, custom_textbook,
                                 ranges, remarks, test_result, achievement):
        if not n_clicks or not student_id:
            raise PreventUpdate
        if not subject or (not textbook_id and not custom_textbook):
            return dbc.Alert("科目と参考書（または自由入力）は必須です。", color="warning"), True, no_update, no_update
        homework_data = [{'date': (date.today() + timedelta(days=i)).strftime('%Y-%m-%d'), 'task': task} for i, task in enumerate(ranges)]
        other_info = {'remarks': remarks, 'test_result': test_result, 'achievement': achievement}
        other_info_json = json.dumps(other_info, ensure_ascii=False)
        success, message = add_or_update_homework(
            student_id, subject, textbook_id, custom_textbook, homework_data, other_info_json
        )
        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': message}
            return "", False, False, toast_data
        else:
            return dbc.Alert(message, color="danger"), True, no_update, no_update

    # 自動割り振りコールバック（変更なし）
    @app.callback(
        Output({'type': 'homework-modal-range-input', 'index': ALL}, 'value', allow_duplicate=True),
        [Input('modal-btn-4-2', 'n_clicks'), Input('modal-btn-2-1', 'n_clicks'), Input('modal-btn-6-0', 'n_clicks')],
        [State('modal-start-page-input', 'value'), State('modal-interval-input', 'value')],
        prevent_initial_call=True
    )
    def auto_assign_homework_in_modal(n_4_2, n_2_1, n_6_0, start_page, interval):
        ctx = callback_context
        if not ctx.triggered or not start_page or not interval:
            raise PreventUpdate
        button_id = ctx.triggered_id.replace('modal-', ''); ranges = []; current_page = start_page; output_values = [''] * 7
        if button_id == 'btn-4-2':
            p, r = 4, 2
            for _ in range(p): end_page = current_page + interval - 1; ranges.append(f"p.{current_page}-{end_page}"); current_page = end_page + 1
            ranges.extend([f"p.{start_page}-{current_page - 1}"] * r)
        elif button_id == 'btn-2-1':
            p, r = 2, 1
            for _ in range(p): end_page = current_page + interval - 1; ranges.append(f"p.{current_page}-{end_page}"); current_page = end_page + 1
            ranges.extend([f"p.{start_page}-{current_page - 1}"] * r)
        elif button_id == 'btn-6-0':
            p = 6
            for _ in range(p): end_page = current_page + interval - 1; ranges.append(f"p.{current_page}-{end_page}"); current_page = end_page + 1
        for i in range(len(ranges)):
            if i < len(output_values): output_values[i] = ranges[i]
        return output_values

    @app.callback(
        Output('delete-homework-confirm', 'displayed'),
        Input('delete-homework-btn', 'n_clicks'),
        prevent_initial_call=True,
    )
    def display_delete_confirmation(n_clicks):
        if n_clicks:
            return True
        return False

    @app.callback(
        [Output('homework-modal-alert', 'children', allow_duplicate=True),
         Output('homework-modal-alert', 'is_open', allow_duplicate=True),
         Output('homework-modal', 'is_open', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True)],
        Input('delete-homework-confirm', 'submit_n_clicks'),
        [State('student-selection-store', 'data'),
         State('editing-homework-store', 'data')],
        prevent_initial_call=True
    )
    def delete_homework_after_confirmation(submit_n_clicks, student_id, editing_data):
        if not submit_n_clicks or not student_id or not editing_data or editing_data.get('mode') != 'edit':
            raise PreventUpdate

        textbook_id = editing_data.get('textbook_id', -1)
        custom_name = editing_data.get('custom_name', '')

        success, message = delete_homework_group(
            student_id,
            textbook_id if textbook_id != -1 else None,
            custom_name
        )

        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message}
        # 成功・失敗に関わらず、アラートは表示せず、モーダルを閉じてトーストで結果を通知
        return "", False, False, toast_data

    @app.callback(
        [Output('homework-modal-custom-textbook-input', 'value', allow_duplicate=True),
         Output({'type': 'homework-modal-range-input', 'index': ALL}, 'value', allow_duplicate=True),
         Output('modal-remarks-input', 'value', allow_duplicate=True),
         Output('modal-test-result-input', 'value', allow_duplicate=True),
         Output('modal-achievement-input', 'value', allow_duplicate=True)],
        Input('clear-homework-modal-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def clear_modal_inputs(n_clicks):
        if not n_clicks:
            raise PreventUpdate

        empty_ranges = [''] * 7
        # 科目と参考書のドロップダウンはクリアしない (no_update を使わない代わりに Output から外す)
        return "", empty_ranges, "", "", None
