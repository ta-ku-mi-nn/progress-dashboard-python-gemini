# callbacks/plan_callbacks.py

import json
import re
from dash import Input, Output, State, html, callback_context, no_update, ALL, MATCH
import dash_bootstrap_components as dbc

from data.nested_json_processor import get_master_textbook_list, get_student_progress, add_or_update_student_progress, get_bulk_presets, get_all_subjects

def register_plan_callbacks(app):
    """学習計画更新モーダルに関連するコールバックを登録します。"""

    # --- ボタンの有効/無効化 (変更なし) ---
    @app.callback(
        [Output('update-plan-btn', 'disabled'),
         Output('open-bulk-modal-btn', 'disabled')],
        Input('student-dropdown', 'value')
    )
    def toggle_plan_buttons(selected_student):
        is_disabled = not selected_student
        return is_disabled, is_disabled

    # --- モーダルの開閉 (変更なし) ---
    @app.callback(
        Output('plan-update-modal', 'is_open'),
        [Input('update-plan-btn', 'n_clicks'), Input('plan-cancel-btn', 'n_clicks'), Input('plan-save-btn', 'n_clicks')],
        State('plan-update-modal', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_plan_modal(open_clicks, cancel_clicks, save_clicks, is_open):
        if open_clicks or cancel_clicks or save_clicks:
            return not is_open
        return no_update

    # --- 科目選択ボタンを生成 (変更なし) ---
    @app.callback(
        Output('plan-subject-selection-container', 'children'),
        Input('plan-update-modal', 'is_open')
    )
    def generate_subject_buttons(is_open):
        if not is_open:
            return []
        subjects = get_all_subjects()
        buttons = [
            dbc.Button(
                subject, 
                id={'type': 'plan-subject-btn', 'subject': subject}, 
                color="primary", 
                outline=True, 
                className="m-1"
            ) for subject in subjects
        ]
        return buttons

    # --- ★★★ 3ステップ制御のコールバック（不具合修正） ★★★ ---
    @app.callback(
        [Output('plan-step-0', 'style'),
         Output('plan-step-1', 'style'),
         Output('plan-step-2', 'style'),
         Output('plan-back-btn', 'style'),
         Output('plan-next-btn', 'style'),
         Output('plan-save-btn', 'style'),
         Output('plan-modal-title', 'children'),
         Output('plan-step-store', 'data'),
         Output('plan-subject-store', 'data', allow_duplicate=True)], # allow_duplicateを追加
        [Input({'type': 'plan-subject-btn', 'subject': ALL}, 'n_clicks'),
         Input('plan-next-btn', 'n_clicks'),
         Input('plan-back-btn', 'n_clicks'),
         Input('plan-update-modal', 'is_open')],
        [State('plan-step-store', 'data'),
         State('plan-subject-store', 'data')],
        prevent_initial_call=True
    )
    def control_modal_steps(subject_clicks, next_clicks, back_clicks, is_open, current_step, stored_subject):
        ctx = callback_context
        if not ctx.triggered:
            return [no_update] * 9

        trigger_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # モーダルを開いた時 -> ステップ0にリセット
        if 'plan-update-modal' in trigger_id_str and is_open:
            return {}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, "ステップ1/3: 科目を選択", 0, ""

        # 科目ボタンが押された時 (ステップ0 -> 1)
        if 'plan-subject-btn' in trigger_id_str and any(subject_clicks):
            clicked_subject = json.loads(trigger_id_str)['subject']
            return {'display': 'none'}, {}, {'display': 'none'}, {}, {}, {'display': 'none'}, f"ステップ2/3: {clicked_subject}の参考書を選択", 1, clicked_subject
        
        # 「次へ」ボタンが押された時 (ステップ1 -> 2)
        if 'plan-next-btn' in trigger_id_str and current_step == 1:
            return {'display': 'none'}, {'display': 'none'}, {}, {}, {'display': 'none'}, {}, "ステップ3/3: 進捗を入力", 2, no_update
        
        # 「戻る」ボタンが押された時
        if 'plan-back-btn' in trigger_id_str:
            # ステップ1 -> 0
            if current_step == 1:
                return {}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, "ステップ1/3: 科目を選択", 0, ""
            # ステップ2 -> 1
            if current_step == 2:
                return {'display': 'none'}, {}, {'display': 'none'}, {}, {}, {'display': 'none'}, f"ステップ2/3: {stored_subject}の参考書を選択", 1, no_update

        return [no_update] * 9

    # --- ★★★ 参考書リストと一括ボタンのコールバック（不具合修正） ★★★ ---
    @app.callback(
        [Output('plan-textbook-list-container', 'children'),
         Output('plan-bulk-buttons-container', 'children'),
         Output('plan-all-books-store', 'data')],
        [Input('plan-subject-store', 'data'),
         Input('plan-search-input', 'value'),
         Input({'type': 'plan-bulk-check-btn', 'books': ALL}, 'n_clicks')],
        [State('school-dropdown', 'value'), 
         State('student-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_textbook_list_and_buttons(subject, search_term, bulk_n_clicks, school, student):
        ctx = callback_context
        trigger_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # 科目が選択されていない、またはステップ1以外では何もしない
        if not subject:
            return no_update, no_update, no_update

        if not all([school, student]):
            return dbc.Alert("生徒が選択されていません。"), [], []

        # --- 一括チェックボタンの処理 ---
        books_to_check = []
        if 'plan-bulk-check-btn' in trigger_id_str and ctx.triggered[0]['value']:
            id_dict = json.loads(trigger_id_str)
            books_to_check = json.loads(id_dict['books'])

        # --- 一括チェックボタン自体の生成 ---
        all_presets = get_bulk_presets()
        subject_presets = all_presets.get(subject, {})
        bulk_buttons = []
        if subject_presets:
            bulk_buttons.append(html.H6("一括チェック:", className="d-inline-block me-2"))
            for preset_name, books in subject_presets.items():
                bulk_buttons.append(dbc.Button(
                    preset_name,
                    id={'type': 'plan-bulk-check-btn', 'books': json.dumps(books)},
                    color='secondary', outline=True, size="sm", className='me-1 mb-2'
                ))
        
        # --- 参考書リストの生成 ---
        master_list = get_master_textbook_list(subject, search_term or "")
        student_progress = get_student_progress(school, student)
        
        accordions = []
        all_book_ids = []
        for level, books in master_list.items():
            checkboxes = []
            for book_name in books:
                book_id = {'type': 'plan-book-checkbox', 'subject': subject, 'level': level, 'book': book_name}
                
                is_checked = student_progress.get(subject, {}).get(level, {}).get(book_name, {}).get('予定', False)
                
                if book_name in books_to_check:
                    is_checked = True

                checkboxes.append(dbc.Checkbox(
                    id=book_id, label=book_name, value=is_checked, className="mb-2"
                ))
                all_book_ids.append(book_id)
            accordions.append(dbc.AccordionItem(title=f"{level} ({len(checkboxes)}件)", children=checkboxes))
        
        return dbc.Accordion(accordions, start_collapsed=False, always_open=True), bulk_buttons, all_book_ids

    # (...以降のコールバックは変更なし...)
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
            progress_str = f"{completed}/{total}" if total != 0 else "0/0"
            
            row_id_str = f"{book_id['subject']}-{book_id['level']}-{book_id['book']}"

            input_group = dbc.InputGroup([
                dbc.Input(
                    id={'type': 'plan-progress-input', 'index': row_id_str},
                    placeholder="例: 50/100",
                    value=progress_str,
                ),
                dbc.Button(
                    "完了",
                    id={'type': 'complete-book-btn', 'index': row_id_str},
                    color="success",
                    outline=True
                ),
            ])

            input_rows.append(dbc.Row([
                dbc.Col(f"{book_id['level']}: {book_id['book']}", width=12, lg=6, className="d-flex align-items-center mb-2 mb-lg-0"),
                dbc.Col(input_group, width=12, lg=6),
            ], className="mb-2 align-items-center"))

        return input_rows, selected_books

    @app.callback(
        Output({'type': 'plan-progress-input', 'index': MATCH}, 'value'),
        Input({'type': 'complete-book-btn', 'index': MATCH}, 'n_clicks'),
        State({'type': 'plan-progress-input', 'index': MATCH}, 'value'),
        prevent_initial_call=True
    )
    def mark_as_complete(n_clicks, current_value):
        if not n_clicks:
            return no_update
        
        match = re.search(r'/(\d+)', current_value)
        if match:
            total_units = match.group(1)
            return f"{total_units}/{total_units}"
        return "100/100"
    
    @app.callback(
        [Output('url', 'href', allow_duplicate=True),
         Output('plan-modal-alert', 'children'),
         Output('plan-modal-alert', 'is_open'),
         Output('success-toast', 'is_open')],
        Input('plan-save-btn', 'n_clicks'),
        [State('school-dropdown', 'value'),
         State('student-dropdown', 'value'),
         State('plan-all-books-store', 'data'),
         State('plan-selected-books-store', 'data'),
         State({'type': 'plan-progress-input', 'index': ALL}, 'value'),
         State({'type': 'plan-progress-input', 'index': ALL}, 'id'),
         State('url', 'pathname')],
        prevent_initial_call=True
    )
    def save_plan_updates(n_clicks, school, student, all_books, selected_books, progress_values, progress_ids, pathname):
        if not n_clicks or not school or not student:
            # ★★★ 修正：all_booksがNoneの場合も考慮 ★★★
            if not all_books:
                # 何もすることがないので、モーダルを閉じてToastを表示する
                return no_update, "", False, True 
            
        progress_map = {p_id['index']: value for p_id, value in zip(progress_ids, progress_values)}
        
        # ★★★ 修正：selected_books が None の場合でも安全に処理する ★★★
        selected_book_names = {f"{b['subject']}-{b['level']}-{b['book']}" for b in selected_books} if selected_books else set()
        
        progress_updates = []

        for book in all_books:
            row_id_str = f"{book['subject']}-{book['level']}-{book['book']}"
            
            if row_id_str in selected_book_names:
                progress_str = progress_map.get(row_id_str, "0/1")
                match = re.match(r'^\s*(\d+)\s*/\s*(\d+)\s*$', progress_str)
                completed_units, total_units = (int(match.group(1)), int(match.group(2))) if match else (0, 1)
                
                progress_updates.append({
                    'subject': book['subject'], 'level': book['level'], 'book_name': book['book'],
                    'is_planned': True,
                    'completed_units': completed_units,
                    'total_units': total_units if total_units > 0 else 1
                })
            else:
                progress_updates.append({
                    'subject': book['subject'], 'level': book['level'], 'book_name': book['book'],
                    'is_planned': False,
                    'completed_units': 0,
                    'total_units': 1
                })

        success, message = add_or_update_student_progress(school, student, progress_updates)
        if success:
            return pathname, "", False, True
        else:
            return no_update, dbc.Alert(message, color="danger"), True, False

    @app.callback(
        Output('bulk-register-modal', 'is_open'),
        [Input('open-bulk-modal-btn', 'n_clicks'),
         Input('close-bulk-modal', 'n_clicks')],
        State('bulk-register-modal', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_bulk_modal(open_clicks, close_clicks, is_open):
        return not is_open

    @app.callback(
        [Output('url', 'href', allow_duplicate=True),
         Output('bulk-register-alert', 'is_open'),
         Output('bulk-register-alert', 'children')],
        Input({'type': 'bulk-plan-button', 'subject': ALL, 'books': ALL}, 'n_clicks'),
        [State('school-dropdown', 'value'),
         State('student-dropdown', 'value'),
         State('url', 'pathname')],
        prevent_initial_call=True
    )
    def handle_bulk_plan_update(n_clicks, school, student, pathname):
        if not any(n_clicks):
            return no_update, False, ""

        ctx = callback_context
        triggered_id = ctx.triggered[0]['prop_id']
        id_dict = json.loads(triggered_id.split('.')[0])
        subject = id_dict['subject']
        books = json.loads(id_dict['books'])
        
        master_list = get_master_textbook_list(subject)
        
        progress_updates = []
        for level, book_names in master_list.items():
            for book_name in book_names:
                if book_name in books:
                    progress_updates.append({
                        'subject': subject,
                        'level': level,
                        'book_name': book_name,
                        'is_planned': True,
                        'completed_units': 0,
                        'total_units': 1
                    })

        if not progress_updates:
            return no_update, True, "対象の参考書が見つかりませんでした。"

        success, message = add_or_update_student_progress(school, student, progress_updates)

        if success:
            return pathname, False, ""
        else:
            return no_update, True, message