# callbacks/plan_callbacks.py

from dash import Input, Output, State, html, dcc, no_update, callback_context, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import json
from datetime import datetime

from data.nested_json_processor import (
    get_master_textbook_list, add_or_update_student_progress, 
    get_student_info_by_id, get_all_subjects, get_student_progress_by_id,
    get_bulk_presets
)

def register_plan_callbacks(app):
    """学習計画モーダルに関連するコールバックを登録します。"""

    @app.callback(
        Output('plan-update-modal', 'is_open'),
        [Input('bulk-register-btn', 'n_clicks'),
         Input('plan-cancel-btn', 'n_clicks'),
         Input('plan-update-toast-trigger', 'data')],
        State('plan-update-modal', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_plan_modal(open_clicks, cancel_clicks, toast_data, is_open):
        ctx = callback_context
        if ctx.triggered_id == 'plan-update-toast-trigger':
            return False
        if open_clicks or cancel_clicks:
            return not is_open
        return is_open

    @app.callback(
        [Output('plan-step-0', 'style'),
         Output('plan-step-1', 'style'),
         Output('plan-step-2', 'style'),
         Output('plan-step-store', 'data'),
         Output('plan-back-btn', 'style'),
         Output('plan-next-btn', 'style'),
         Output('plan-save-btn', 'style')],
        [Input('plan-update-modal', 'is_open'),
         Input('plan-next-btn', 'n_clicks'),
         Input('plan-back-btn', 'n_clicks'),
         Input('plan-subject-store', 'data')],
        State('plan-step-store', 'data'),
        prevent_initial_call=True
    )
    def control_plan_steps(is_open, next_clicks, back_clicks, subject, current_step):
        ctx = callback_context
        step = current_step

        if (ctx.triggered_id == 'plan-update-modal' and is_open) or (ctx.triggered_id == 'plan-cancel-btn'):
            step = 0
        elif ctx.triggered_id == 'plan-subject-store' and subject:
            step = 1
        elif ctx.triggered_id == 'plan-next-btn':
            step += 1
        elif ctx.triggered_id == 'plan-back-btn':
            step -= 1
        
        step = max(0, min(step, 2))
        styles = [{'display': 'none'}] * 3
        styles[step] = {'display': 'block'}
        
        back_style = {'display': 'inline-block'} if step > 0 else {'display': 'none'}
        next_style = {'display': 'inline-block'} if step < 2 else {'display': 'none'}
        save_style = {'display': 'inline-block'} if step == 2 else {'display': 'none'}

        return styles[0], styles[1], styles[2], step, back_style, next_style, save_style

    @app.callback(
        Output('plan-modal-title', 'children'),
        [Input('plan-step-store', 'data')],
        [State('plan-subject-store', 'data'), State('student-selection-store', 'data')]
    )
    def update_modal_title(step, subject, student_id):
        student_name = get_student_info_by_id(student_id).get('name', '') if student_id else ""
        base_title = f"{student_name}さん の学習計画"
        
        if step == 0: return f"{base_title} - ステップ1: 科目選択"
        if step == 1: return f"{base_title} - ステップ2: 参考書選択 ({subject})"
        if step == 2: return f"{base_title} - ステップ3: 進捗入力 ({subject})"
        return base_title

    @app.callback(
        [Output('plan-subject-selection-container', 'children'),
         Output('plan-current-progress-store', 'data'),
         Output('plan-subject-store', 'data')],
        [Input('plan-update-modal', 'is_open'),
         Input({'type': 'plan-subject-btn', 'subject': ALL}, 'n_clicks')],
        [State('student-selection-store', 'data')],
        prevent_initial_call=True
    )
    def handle_subject_selection(is_open, subject_clicks, student_id):
        ctx = callback_context
        triggered_id = ctx.triggered_id
        
        all_subjects = get_all_subjects()
        
        def create_buttons(active_subject=None):
            return [dbc.Button(s, id={'type': 'plan-subject-btn', 'subject': s}, 
                               color="primary", outline= (s != active_subject), className="m-1") 
                    for s in all_subjects]

        if triggered_id == 'plan-update-modal' and is_open:
            if not student_id: return dbc.Alert("生徒が選択されていません。"), {}, None
            if not all_subjects: return dbc.Alert("科目が登録されていません。"), {}, None
            return create_buttons(), {}, None

        if isinstance(triggered_id, dict) and triggered_id.get('type') == 'plan-subject-btn':
            subject = triggered_id['subject']
            progress = get_student_progress_by_id(student_id)
            
            subject_progress = {}
            if subject in progress:
                for level, books in progress[subject].items():
                    for book, details in books.items():
                        if details.get('予定'):
                            subject_progress[book] = {
                                'completed': details.get('completed_units', 0),
                                'total': details.get('total_units', 1)
                            }
            return create_buttons(active_subject=subject), subject_progress, subject
        
        return no_update, no_update, no_update

    @app.callback(
        Output('plan-selected-books-store', 'data'),
        [Input('plan-subject-store', 'data'),
         Input({'type': 'plan-book-checklist', 'level': ALL}, 'value'),
         Input({'type': 'plan-preset-btn', 'books': ALL}, 'n_clicks'),
         Input('plan-uncheck-all-btn', 'n_clicks')],
        [State('plan-selected-books-store', 'data'),
         State('plan-current-progress-store', 'data')],
        prevent_initial_call=True
    )
    def update_selected_books_store_combined(subject, checklist_vals, preset_clicks, uncheck_clicks, current_selection, current_progress):
        ctx = callback_context
        tid = ctx.triggered_id

        if tid == 'plan-subject-store':
            return list(current_progress.keys())
        
        if tid == 'plan-uncheck-all-btn':
            return []
        
        if isinstance(tid, dict) and tid.get('type') == 'plan-book-checklist':
            # 検索などで表示されていない書籍の選択状態を維持するため、現在の選択と結合する
            current_visible_books = {book for sub in checklist_vals for book in sub}
            other_selected_books = [book for book in current_selection if book not in current_visible_books]
            
            new_selection = list(current_visible_books) + other_selected_books
            return sorted(list(set(new_selection)))

        if isinstance(tid, dict) and tid.get('type') == 'plan-preset-btn':
            new_books = json.loads(tid['books'])
            return sorted(list(set(current_selection + new_books)))

        return no_update

    @app.callback(
        Output('plan-textbook-list-container', 'children'),
        [Input('plan-search-input', 'value'),
         Input('plan-selected-books-store', 'data')],
        State('plan-subject-store', 'data'),
        prevent_initial_call=True
    )
    def update_textbook_checklist(search_term, selected_books, subject):
        if not subject: return []
        
        textbooks_by_level = get_master_textbook_list(subject, search_term)
        if not textbooks_by_level: return dbc.Alert("この科目の参考書がありません。", color="info")

        items = [dbc.AccordionItem(
            dbc.Checklist(
                options=[{'label': b, 'value': b} for b in books],
                value=[b for b in selected_books if b in books],
                id={'type': 'plan-book-checklist', 'level': level}
            ), title=f"レベル: {level} ({len(books)}冊)") for level, books in textbooks_by_level.items()]
        return dbc.Accordion(items, start_collapsed=False, always_open=True)

    @app.callback(Output('plan-preset-buttons-container', 'children'), Input('plan-subject-store', 'data'), prevent_initial_call=True)
    def update_preset_buttons(subject):
        if not subject: return []
        presets = get_bulk_presets()
        if subject not in presets: return dbc.Alert("この科目のプリセットはありません。", color="info")
        
        buttons = [dbc.Button(p, id={'type': 'plan-preset-btn', 'books': json.dumps(b)}, color="secondary", className="m-1") for p, b in presets[subject].items()]
        return buttons

    @app.callback(Output('plan-selected-books-display', 'children'), Input('plan-selected-books-store', 'data'))
    def update_selected_books_display(selected_books):
        if not selected_books: return dbc.Alert("参考書が選択されていません。", color="secondary", className="p-2")
        return dbc.ListGroup([dbc.ListGroupItem(b, className="p-2") for b in sorted(selected_books)], flush=True)

    @app.callback(
        Output('plan-progress-input-container', 'children'),
        Input('plan-step-2', 'style'),
        [State('plan-selected-books-store', 'data'), State('plan-subject-store', 'data'), State('plan-current-progress-store', 'data')]
    )
    def create_progress_inputs(step2_style, selected_books, subject, current_progress):
        if not selected_books or step2_style.get('display') == 'none': return no_update
            
        master_books = get_master_textbook_list(subject)
        inputs = []
        for book in sorted(selected_books):
            level = next((lvl for lvl, b_list in master_books.items() if book in b_list), "N/A")
            prog = current_progress.get(book, {})
            val = f"{prog.get('completed', '')}/{prog.get('total', '')}".strip('/')
            
            inputs.append(html.Div([
                html.H6(f"[{level}] {book}", className="mt-3"),
                dbc.InputGroup([
                    dbc.Input(id={'type': 'plan-progress-input', 'book': book}, placeholder="例: 10/25", value=val),
                    dbc.Button("達成", id={'type': 'plan-progress-done-btn', 'book': book}, color="success", outline=True)
                ]),
                dcc.Store(id={'type': 'plan-book-level-store', 'book': book}, data=level)
            ], className="mb-2"))
        return inputs
        
    @app.callback(
        Output({'type': 'plan-progress-input', 'book': MATCH}, 'value'),
        Input({'type': 'plan-progress-done-btn', 'book': MATCH}, 'n_clicks'),
        prevent_initial_call=True
    )
    def mark_as_done(n_clicks):
        if not n_clicks: return no_update
        return "1/1"

    @app.callback(Output('plan-next-btn', 'disabled'),[Input('plan-step-store', 'data'), Input('plan-subject-store', 'data'), Input('plan-selected-books-store', 'data')])
    def control_next_button_state(step, subject, selected_books):
        if step == 0 and not subject: return True
        if step == 1 and not selected_books: return True
        return False
        
    @app.callback(
        [Output('plan-modal-alert', 'children'),
         Output('plan-modal-alert', 'is_open'),
         Output('plan-update-toast-trigger', 'data')],
        Input('plan-save-btn', 'n_clicks'),
        [State('student-selection-store', 'data'),
         State('plan-subject-store', 'data'),
         State({'type': 'plan-book-level-store', 'book': ALL}, 'data'),
         State({'type': 'plan-book-level-store', 'book': ALL}, 'id'),
         State({'type': 'plan-progress-input', 'book': ALL}, 'value'),
         State('plan-current-progress-store', 'data')],
        prevent_initial_call=True
    )
    def save_plan_progress(n_clicks, student_id, subject, levels, book_ids, progress_values, current_progress):
        if not n_clicks: return no_update, no_update, no_update

        student_info = get_student_info_by_id(student_id)
        if not student_info: return dbc.Alert("生徒情報取得失敗。", color="danger"), True, no_update
            
        updates = []
        all_selected_books = [id_dict['book'] for id_dict in book_ids]
        
        books_to_unplan = [book for book in current_progress.keys() if book not in all_selected_books]

        for book in books_to_unplan:
            level = next((lvl for lvl, b_list in get_master_textbook_list(subject).items() if book in b_list), "N/A")
            updates.append({'subject': subject, 'level': level, 'book_name': book, 'is_planned': False, 'completed_units': 0, 'total_units': 1})
            
        for i, id_dict in enumerate(book_ids):
            book_name = id_dict['book']
            val = progress_values[i]
            
            completed, total = 0, 1
            if val is None or val.strip() == "":
                if book_name in current_progress:
                    prog = current_progress[book_name]
                    completed = prog.get('completed', 0)
                    total = prog.get('total', 1)
                else:
                    completed, total = 0, 1
            elif "/" in val:
                try: completed, total = map(int, val.split('/'))
                except (ValueError, TypeError): return dbc.Alert(f"「{book_name}」の進捗入力が不正です。", color="danger"), True, no_update
            else:
                try: completed, total = int(val), 1
                except (ValueError, TypeError): return dbc.Alert(f"「{book_name}」の進捗入力が不正です。", color="danger"), True, no_update

            updates.append({
                'subject': subject, 'level': levels[i], 'book_name': book_name, 'is_planned': True,
                'completed_units': completed, 'total_units': total if total > 0 else 1
            })

        if not updates:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': '更新する内容がありません。'}
            return None, False, toast_data

        success, message = add_or_update_student_progress(student_info['school'], student_info['name'], updates)

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': '学習計画を更新しました。'}
            return None, False, toast_data
        else:
            return dbc.Alert(message, color="danger"), True, no_update