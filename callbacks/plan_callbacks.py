# callbacks/plan_callbacks.py

import json
import datetime
import re
from dash import Input, Output, State, html, callback_context, no_update, ALL
import dash_bootstrap_components as dbc

from data.nested_json_processor import get_master_textbook_list, get_student_progress, add_or_update_student_progress

def register_plan_callbacks(app):
    """学習計画更新モーダルに関連するコールバックを登録します。"""

    # --- (toggle_plan_button, toggle_plan_modal, update_textbook_list, control_modal_steps は変更なし) ---
    @app.callback(Output('update-plan-btn', 'disabled'), Input('student-dropdown', 'value'))
    def toggle_plan_button(selected_student): return not selected_student
    @app.callback(Output('plan-update-modal', 'is_open'), [Input('update-plan-btn', 'n_clicks'), Input('plan-cancel-btn', 'n_clicks'), Input('plan-save-btn', 'n_clicks')], [State('plan-update-modal', 'is_open')], prevent_initial_call=True)
    def toggle_plan_modal(open_clicks, cancel_clicks, save_clicks, is_open):
        ctx = callback_context
        if not ctx.triggered: return no_update
        return not is_open
    @app.callback(Output('plan-textbook-list-container', 'children'), [Input('plan-subject-dropdown', 'value'), Input('plan-search-input', 'value')], [State('school-dropdown', 'value'), State('student-dropdown', 'value')], prevent_initial_call=True)
    def update_textbook_list(subject, search_term, school, student):
        if not subject or not school or not student: return []
        master_list = get_master_textbook_list(subject, search_term or "")
        student_progress = get_student_progress(school, student)
        if not master_list: return dbc.Alert("該当する参考書が見つかりません。", color="info")
        accordions = []
        for level, books in master_list.items():
            checkboxes = [dbc.Checkbox(id={'type': 'plan-book-checkbox', 'subject': subject, 'level': level, 'book': book_name}, label=book_name, value=student_progress.get(subject, {}).get(level, {}).get(book_name, {}).get('予定', False), className="mb-2") for book_name in books]
            accordions.append(dbc.AccordionItem(title=f"{level} ({len(checkboxes)}件)", children=checkboxes))
        return dbc.Accordion(accordions, start_collapsed=False, always_open=True)
    @app.callback([Output('plan-step-1', 'style'), Output('plan-step-2', 'style'), Output('plan-back-btn', 'style'), Output('plan-next-btn', 'style'), Output('plan-save-btn', 'style'), Output('plan-modal-title', 'children'), Output('plan-step-store', 'data')], [Input('plan-next-btn', 'n_clicks'), Input('plan-back-btn', 'n_clicks'), Input('plan-cancel-btn', 'n_clicks'), Input('plan-update-modal', 'is_open')], [State('plan-step-store', 'data')], prevent_initial_call=True)
    def control_modal_steps(next_clicks, back_clicks, cancel_clicks, is_open, current_step):
        ctx = callback_context
        if not ctx.triggered: return no_update, no_update, no_update, no_update, no_update, no_update, no_update
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if trigger_id == 'plan-update-modal' and is_open or trigger_id == 'plan-cancel-btn': return {}, {'display': 'none'}, {'display': 'none'}, {}, {'display': 'none'}, "ステップ1: 学習計画の選択", 1
        if trigger_id == 'plan-next-btn' and current_step == 1: return {'display': 'none'}, {}, {}, {'display': 'none'}, {}, "ステップ2: 進捗の入力", 2
        if trigger_id == 'plan-back-btn' and current_step == 2: return {}, {'display': 'none'}, {'display': 'none'}, {}, {'display': 'none'}, "ステップ1: 学習計画の選択", 1
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update

    # --- ★★★ generate_progress_inputs と save_plan_updates を修正 ★★★ ---

    @app.callback(
        [Output('plan-progress-input-container', 'children'),
         Output('plan-selected-books-store', 'data')],
        Input('plan-step-store', 'data'),
        [State({'type': 'plan-book-checkbox', 'subject': ALL, 'level': ALL, 'book': ALL}, 'value'),
         State({'type': 'plan-book-checkbox', 'subject': ALL, 'level': ALL, 'book': ALL}, 'id'),
         State('school-dropdown', 'value'),
         State('student-dropdown', 'value')],
        prevent_initial_call=True
    )
    def generate_progress_inputs(current_step, checkbox_values, checkbox_ids, school, student):
        if current_step != 2:
            return no_update, no_update
            
        selected_books = [checkbox_ids[i] for i, value in enumerate(checkbox_values) if value]
        if not selected_books:
            return dbc.Alert("計画に追加する参考書が選択されていません。「戻る」ボタンで選択してください。", color="warning"), no_update

        student_progress = get_student_progress(school, student)
        
        input_rows = []
        for book_id in selected_books:
            progress = student_progress.get(book_id['subject'], {}).get(book_id['level'], {}).get(book_id['book'], {})
            completed = progress.get('completed_units', 0)
            total = progress.get('total_units', 1)
            # 達成済みの場合は 1/1 と表示
            progress_str = f"{completed}/{total}" if total != 0 else "0/0"
            
            row_id_str = f"{book_id['subject']}-{book_id['level']}-{book_id['book']}"

            input_rows.append(dbc.Row([
                dbc.Col(f"{book_id['level']}: {book_id['book']}", width=7, className="d-flex align-items-center"),
                dbc.Col(dbc.Input(
                    id={'type': 'plan-progress-input', 'id': row_id_str},
                    placeholder="例: 50/100",
                    value=progress_str,
                ), width=5),
            ], className="mb-2"))

        return input_rows, selected_books

    @app.callback(
        [Output('url', 'href'),
         Output('plan-modal-alert', 'children'),
         Output('plan-modal-alert', 'is_open')],
        Input('plan-save-btn', 'n_clicks'),
        [State('school-dropdown', 'value'),
         State('student-dropdown', 'value'),
         State('plan-selected-books-store', 'data'),
         State({'type': 'plan-progress-input', 'id': ALL}, 'value'),
         State({'type': 'plan-progress-input', 'id': ALL}, 'id'),
         State('url', 'pathname')],
        prevent_initial_call=True
    )
    def save_plan_updates(n_clicks, school, student, selected_books, progress_values, progress_ids, pathname):
        if not n_clicks or not school or not student or not selected_books:
            return no_update, no_update, False

        progress_map = {p_id['id']: value for p_id, value in zip(progress_ids, progress_values)}
        progress_updates = []
        
        for book in selected_books:
            row_id_str = f"{book['subject']}-{book['level']}-{book['book']}"
            progress_str = progress_map.get(row_id_str, "0/1")
            
            # 分数形式の文字列をパース
            match = re.match(r'^\s*(\d+)\s*/\s*(\d+)\s*$', progress_str)
            if match:
                completed_units, total_units = int(match.group(1)), int(match.group(2))
            else: # 不正な形式の場合は0/1として扱う
                completed_units, total_units = 0, 1
            
            progress_updates.append({
                'subject': book['subject'], 'level': book['level'], 'book_name': book['book'],
                'is_planned': True,
                'completed_units': completed_units,
                'total_units': total_units if total_units > 0 else 1 # 0除算を防ぐ
            })

        success, message = add_or_update_student_progress(school, student, progress_updates)
        if success:
            return pathname, "", False
        else:
            return no_update, dbc.Alert(message, color="danger"), True