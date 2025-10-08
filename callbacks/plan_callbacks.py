# callbacks/plan_callbacks.py

from dash import Input, Output, State, html, dcc, no_update, callback_context, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime

from data.nested_json_processor import get_master_textbook_list, add_or_update_student_progress, get_student_info_by_id, get_all_subjects

def register_plan_callbacks(app):
    """学習計画モーダル（一括登録）に関連するコールバックを登録します。"""

    # --- ★★★ ここから全体を修正（参照コードに基づき、安定版に戻します） ★★★

    @app.callback(
        Output('plan-update-modal', 'is_open'),
        [Input('bulk-register-btn', 'n_clicks'),
         Input('plan-cancel-btn', 'n_clicks'),
         Input('plan-save-btn', 'n_clicks')],
        [State('plan-update-modal', 'is_open'),
         State('plan-modal-alert', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_plan_modal(open_clicks, cancel_clicks, save_clicks, is_open, alert_is_open):
        ctx = callback_context
        trigger_id = ctx.triggered_id
        if trigger_id == 'plan-save-btn' and not alert_is_open:
            return False
        if trigger_id in ['bulk-register-btn', 'plan-cancel-btn']:
            return not is_open
        return is_open

    # --- ステップ表示制御 ---
    @app.callback(
        [Output('plan-step-0', 'style'),
         Output('plan-step-1', 'style'),
         Output('plan-step-2', 'style'),
         Output('plan-step-store', 'data')],
        [Input('plan-update-modal', 'is_open'),
         Input('plan-subject-store', 'data'),
         Input('plan-next-btn', 'n_clicks'),
         Input('plan-back-btn', 'n_clicks')],
        [State('plan-step-store', 'data')],
        prevent_initial_call=True
    )
    def update_plan_step(is_open, subject, next_clicks, back_clicks, current_step):
        ctx = callback_context
        trigger_id = ctx.triggered_id
        step = current_step or 0

        if trigger_id == 'plan-update-modal' and is_open:
            step = 0
        elif trigger_id == 'plan-subject-store' and subject:
            step = 1
        elif trigger_id == 'plan-next-btn':
            step = 2
        elif trigger_id == 'plan-back-btn':
            step = max(step - 1, 0)

        styles = [{'display': 'none'}] * 3
        styles[step] = {'display': 'block'}
        return styles[0], styles[1], styles[2], step

    # --- ボタンの有効/無効制御 ---
    @app.callback(
        [Output('plan-next-btn', 'disabled'),
         Output('plan-save-btn', 'disabled')],
        [Input('plan-selected-books-store', 'data'),
         Input('plan-step-store', 'data')]
    )
    def toggle_action_buttons_disabled(selected_books, step):
        next_disabled = (step == 1 and not selected_books) or step != 1
        save_disabled = step != 2 or not selected_books
        return next_disabled, save_disabled

    # --- モーダルタイトルの更新 ---
    @app.callback(
        Output('plan-modal-title', 'children'),
        [Input('plan-step-store', 'data')],
        [State('plan-subject-store', 'data'),
         State('student-selection-store', 'data')]
    )
    def update_modal_title(step, subject, student_id):
        student_name = ""
        if student_id:
            student_info = get_student_info_by_id(student_id)
            student_name = student_info.get('name', '')
        base_title = f"{student_name}さん の学習計画"
        if step == 0: return f"{base_title} - ステップ1: 科目選択"
        if step == 1: return f"{base_title} - ステップ2: 参考書選択 ({subject})"
        if step == 2: return f"{base_title} - ステップ3: 進捗入力 ({subject})"
        return base_title

    # --- 科目選択ボタンの生成 ---
    @app.callback(
        Output('plan-subject-selection-container', 'children'),
        Input('plan-update-modal', 'is_open'),
        State('student-selection-store', 'data')
    )
    def update_subject_selector(is_open, student_id):
        if not is_open or not student_id:
            return no_update
            
        all_subjects = get_all_subjects()
        if not all_subjects:
            return dbc.Alert("登録されている科目がありません。", color="warning")

        return dbc.ListGroup(
            [dbc.ListGroupItem(
                subject, id={'type': 'plan-subject-btn', 'subject': subject}, action=True, n_clicks=0
            ) for subject in all_subjects]
        )

    # --- 科目選択のハンドリング ---
    @app.callback(
        Output('plan-subject-store', 'data'),
        Input({'type': 'plan-subject-btn', 'subject': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def store_plan_subject(n_clicks):
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks):
            raise PreventUpdate
        return ctx.triggered_id['subject']

    # --- 参考書リストの更新 ---
    @app.callback(
        [Output('plan-textbook-list-container', 'children'),
         Output('plan-all-books-store', 'data'),
         Output('loading-textbooks', 'children')],
        [Input('plan-subject-store', 'data'),
         Input('plan-search-input', 'value')],
        [State('plan-step-store', 'data')],
        prevent_initial_call=True
    )
    def update_textbook_list(subject, search_term, step):
        if step != 1 or not subject:
            return no_update, no_update, ""
            
        textbooks_by_level = get_master_textbook_list(subject, search_term)
        
        if not textbooks_by_level:
            return dbc.Alert("この科目の参考書マスターが登録されていません。", color="warning"), {}, ""

        all_books_flat = []
        accordion_items = []
        for level, books in textbooks_by_level.items():
            all_books_flat.extend(books)
            accordion_items.append(
                dbc.AccordionItem(
                    dbc.Checklist(
                        options=[{'label': book, 'value': book} for book in books],
                        id={'type': 'plan-book-checklist', 'level': level},
                        value=[]
                    ),
                    title=f"レベル: {level} ({len(books)}冊)"
                )
            )
        
        return dbc.Accordion(accordion_items, start_collapsed=True, always_open=True, className="mt-2"), all_books_flat, ""

    # --- 選択された参考書の保存 ---
    @app.callback(
        Output('plan-selected-books-store', 'data'),
        Input({'type': 'plan-book-checklist', 'level': ALL}, 'value'),
        prevent_initial_call=True
    )
    def update_selected_books_store(selected_values):
        flat_list = [item for sublist in selected_values if sublist for item in sublist]
        return flat_list

    # --- 全チェック解除 ---
    @app.callback(
        Output({'type': 'plan-book-checklist', 'level': ALL}, 'value'),
        Input('plan-uncheck-all-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def uncheck_all_books(n_clicks):
        if not n_clicks:
            raise PreventUpdate
        return [[] for _ in callback_context.outputs_list]

    # --- 進捗入力エリアの生成 ---
    @app.callback(
        [Output('plan-progress-input-container', 'children'),
         Output('loading-progress-inputs', 'children')],
        Input('plan-step-2', 'style'),
        [State('plan-selected-books-store', 'data'),
         State('plan-subject-store', 'data')]
    )
    def update_progress_input_area(step_style, selected_books, subject):
        if not step_style or step_style.get('display') == 'none' or not selected_books:
            return no_update, ""
        master_books = get_master_textbook_list(subject)
        inputs = []
        for book in selected_books:
            level_found = ""
            for level, books_in_level in master_books.items():
                if book in books_in_level:
                    level_found = level
                    break
            inputs.append(html.Div([
                html.H6(f"[{level_found}] {book}", className="mt-3"),
                dbc.Row([
                    dbc.Col(dcc.Input(id={'type': 'plan-completed-units', 'book': book}, type='number', placeholder='完了ユニット数', min=0), width=6),
                    dbc.Col(dcc.Input(id={'type': 'plan-total-units', 'book': book}, type='number', placeholder='総ユニット数', min=1), width=6),
                ]),
                dcc.Store(id={'type': 'plan-book-level-store', 'book': book}, data=level_found)
            ]))
        return inputs, ""

    # --- 保存処理 ---
    @app.callback(
        [Output('plan-modal-alert', 'children'),
         Output('plan-modal-alert', 'is_open')],
        Input('plan-save-btn', 'n_clicks'),
        [State('student-selection-store', 'data'),
         State('plan-subject-store', 'data'),
         State('plan-selected-books-store', 'data'),
         State({'type': 'plan-book-level-store', 'book': ALL}, 'data'),
         State({'type': 'plan-completed-units', 'book': ALL}, 'value'),
         State({'type': 'plan-total-units', 'book': ALL}, 'value'),
         ],
        prevent_initial_call=True
    )
    def save_plan_progress(
        n_clicks, student_id, subject, selected_books,
        levels, completed_units, total_units
    ):
        if not n_clicks or not student_id:
            return no_update, no_update
        student_info = get_student_info_by_id(student_id)
        if not student_info:
            return dbc.Alert("生徒情報の取得に失敗しました。", color="danger"), True
        school = student_info.get('school')
        student_name = student_info.get('name')
        updates = []
        for i, book in enumerate(selected_books):
            updates.append({
                'subject': subject,
                'level': levels[i],
                'book_name': book,
                'is_planned': True,
                'completed_units': completed_units[i] or 0,
                'total_units': total_units[i] or 1
            })
        success, message = add_or_update_student_progress(school, student_name, updates)
        if success:
            return None, False
        else:
            return dbc.Alert(message, color="danger"), True