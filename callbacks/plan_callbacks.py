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
        [Input({'type': 'open-plan-modal', 'index': ALL}, 'n_clicks'),
         Input('plan-cancel-btn', 'n_clicks'),
         Input('toast-trigger', 'data')],
        State('plan-update-modal', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_plan_modal(open_clicks, cancel_clicks, toast_data, is_open):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        open_button_clicked = any(n_clicks for n_clicks in open_clicks if n_clicks)

        triggered_id = ctx.triggered_id

        if triggered_id == 'toast-trigger':
            if toast_data and toast_data.get('source') == 'plan':
                return False
            return no_update

        if (isinstance(triggered_id, dict) and triggered_id.get('type') == 'open-plan-modal' and open_button_clicked) or \
           (triggered_id == 'plan-cancel-btn' and cancel_clicks):
            return not is_open

        return no_update

    @app.callback(
        [Output('plan-step-0', 'style'),
         Output('plan-step-1', 'style'),
         Output('plan-step-2', 'style'),
         Output('plan-step-store', 'data'),
         Output('plan-back-btn', 'style'),
         Output('plan-next-btn', 'style'),
         Output('plan-save-btn', 'style'),
         Output('plan-empty-confirm-dialog', 'displayed')],
        [Input('plan-update-modal', 'is_open'),
         Input('plan-next-btn', 'n_clicks'),
         Input('plan-back-btn', 'n_clicks'),
         Input('plan-subject-store', 'data')],
        [State('plan-step-store', 'data'),
         State('plan-selected-books-store', 'data')],
        prevent_initial_call=True
    )
    def control_plan_steps(is_open, next_clicks, back_clicks, subject, current_step, selected_books):
        ctx = callback_context
        triggered_id = ctx.triggered_id

        step = current_step
        show_dialog = False

        if (triggered_id == 'plan-update-modal' and is_open):
            step = 0
        elif triggered_id == 'plan-subject-store' and subject:
            step = 1
        elif triggered_id == 'plan-back-btn':
            step -= 1
        elif triggered_id == 'plan-next-btn':
            if current_step == 1 and not selected_books:
                show_dialog = True
            else:
                step += 1

        step = max(0, min(step, 2))

        if show_dialog:
            step = current_step

        styles = [{'display': 'none'}] * 3
        styles[step] = {'display': 'block'}

        back_style = {'display': 'inline-block'} if step > 0 else {'display': 'none'}
        next_style = {'display': 'inline-block'} if step < 2 else {'display': 'none'}
        save_style = {'display': 'inline-block'} if step == 2 else {'display': 'none'}

        return styles[0], styles[1], styles[2], step, back_style, next_style, save_style, show_dialog

    @app.callback(
        Output('plan-modal-title', 'children'),
        [Input('plan-step-store', 'data')],
        [State('plan-subject-store', 'data'), State('student-selection-store', 'data')]
    )
    def update_modal_title(step, subject, student_id):
        student_name = get_student_info_by_id(student_id).get('name', '') if student_id else ""
        base_title = f"{student_name}さん の学習計画"

        if step == 0: return "①科目選択"
        if step == 1: return f"②参考書選択 ({subject})"
        if step == 2: return f"③進捗入力 ({subject})"
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
         Input('plan-uncheck-all-btn', 'n_clicks'),
         Input('add-custom-book-btn', 'n_clicks')],
        [State('plan-selected-books-store', 'data'),
         State('plan-current-progress-store', 'data'),
         State('custom-book-name-input', 'value')],
        prevent_initial_call=True
    )
    def update_selected_books_store_combined(subject, checklist_vals, preset_clicks, uncheck_clicks, add_custom_clicks, current_selection, current_progress, custom_book_name):
        ctx = callback_context
        tid = ctx.triggered_id

        if not ctx.triggered:
            raise PreventUpdate

        if tid == 'plan-subject-store':
            return list(current_progress.keys())

        if tid == 'plan-uncheck-all-btn':
            return []

        if isinstance(tid, dict) and tid.get('type') == 'plan-book-checklist':
            selected_in_checklists = {book for sublist in checklist_vals if sublist for book in sublist}
            return sorted(list(selected_in_checklists))

        if isinstance(tid, dict) and tid.get('type') == 'plan-preset-btn':
            new_books = json.loads(tid['books'])
            return sorted(list(set((current_selection or []) + new_books)))

        if tid == 'add-custom-book-btn' and custom_book_name:
            new_selection = (current_selection or []) + [custom_book_name]
            return sorted(list(set(new_selection)))

        return no_update

    @app.callback(
        [Output('plan-custom-books-store', 'data'),
         Output('custom-book-name-input', 'value'),
         Output('custom-book-level-input', 'value'),
         Output('custom-book-duration-input', 'value')],
        Input('add-custom-book-btn', 'n_clicks'),
        [State('custom-book-name-input', 'value'),
         State('custom-book-level-input', 'value'),
         State('custom-book-duration-input', 'value'),
         State('plan-custom-books-store', 'data')],
        prevent_initial_call=True
    )
    def add_custom_book_to_store(n_clicks, name, level, duration, current_custom_books):
        if not n_clicks or not all([name, level, duration is not None]):
            raise PreventUpdate

        updated_custom_books = current_custom_books or {}
        updated_custom_books[name] = {
            'level': level,
            'duration': float(duration)
        }
        return updated_custom_books, "", "", None

    @app.callback(
        Output('plan-textbook-list-container', 'children'),
        [Input('plan-search-input', 'value'),
         Input('plan-subject-store', 'data'),
         Input('plan-selected-books-store', 'data')],
        prevent_initial_call=True
    )
    def update_textbook_checklist(search_term, subject, selected_books):
        if not subject: return []

        textbooks_by_level = get_master_textbook_list(subject, search_term)
        if not textbooks_by_level: return dbc.Alert("この科目の参考書がありません。", color="info")

        items = [dbc.AccordionItem(
            dbc.Checklist(
                options=[{'label': b, 'value': b} for b in books],
                value=[b for b in (selected_books or []) if b in books],
                id={'type': 'plan-book-checklist', 'level': level}
            ), title=f"レベル: {level} ({len(books)}冊)") for level, books in textbooks_by_level.items()]

        return dbc.Accordion(items, start_collapsed=False, always_open=True, persistence=True, persistence_type='session', id='plan-accordion')

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
        [State('plan-selected-books-store', 'data'),
         State('plan-subject-store', 'data'),
         State('plan-current-progress-store', 'data'),
         State('plan-custom-books-store', 'data')]
    )
    def create_progress_inputs(step2_style, selected_books, subject, current_progress, custom_books):
        if not selected_books or (step2_style and step2_style.get('display') == 'none'):
            return no_update

        master_books = get_master_textbook_list(subject)
        all_books_with_levels = []
        for book in selected_books:
            if book in (custom_books or {}):
                level = custom_books[book]['level']
            else:
                level = next((lvl for lvl, b_list in master_books.items() if book in b_list), "N/A")
            all_books_with_levels.append({'name': book, 'level': level})

        level_order = ['基礎徹底', '日大', 'MARCH', '早慶']
        sorted_books = sorted(
            all_books_with_levels,
            key=lambda x: (level_order.index(x['level']) if x['level'] in level_order else len(level_order), x['name'])
        )

        inputs = []
        for book_info in sorted_books:
            book_name = book_info['name']
            level = book_info['level']

            prog = (current_progress or {}).get(book_name, {})
            val = f"{prog.get('completed', '')}/{prog.get('total', '')}".strip('/')

            input_row = dbc.Row([
                dbc.Col(
                    html.Label(f"[{level}] {book_name}", className="col-form-label"),
                    width=12, lg=6
                ),
                dbc.Col(
                    dbc.InputGroup([
                        dbc.Input(id={'type': 'plan-progress-input', 'book': book_name}, placeholder="例: 10/25", value=val),
                        dbc.Button("達成", id={'type': 'plan-progress-done-btn', 'book': book_name}, color="success", outline=True)
                    ]),
                    width=12, lg=6
                ),
                dcc.Store(id={'type': 'plan-book-level-store', 'book': book_name}, data=level)
            ], className="mb-2 align-items-center")
            inputs.append(input_row)

        return inputs

    @app.callback(
        Output({'type': 'plan-progress-input', 'book': MATCH}, 'value'),
        Input({'type': 'plan-progress-done-btn', 'book': MATCH}, 'n_clicks'),
        prevent_initial_call=True
    )
    def mark_as_done(n_clicks):
        if not n_clicks: return no_update
        return "1/1"

    @app.callback(Output('plan-next-btn', 'disabled'),[Input('plan-step-store', 'data'), Input('plan-subject-store', 'data')])
    def control_next_button_state(step, subject):
        if step == 0 and not subject: return True
        return False

    @app.callback(
        [Output('plan-modal-alert', 'children'),
         Output('plan-modal-alert', 'is_open'),
         Output('toast-trigger', 'data', allow_duplicate=True)],
        [Input('plan-save-btn', 'n_clicks'),
         Input('plan-empty-confirm-dialog', 'submit_n_clicks')],
        [State('student-selection-store', 'data'),
         State('plan-subject-store', 'data'),
         State({'type': 'plan-book-level-store', 'book': ALL}, 'data'),
         State({'type': 'plan-book-level-store', 'book': ALL}, 'id'),
         State({'type': 'plan-progress-input', 'book': ALL}, 'value'),
         State('plan-current-progress-store', 'data'),
         State('plan-custom-books-store', 'data')],
        prevent_initial_call=True
    )
    def save_plan_progress(save_clicks, confirm_clicks, student_id, subject, levels, book_ids, progress_values, current_progress, custom_books):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        if not student_id:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': 'エラー: 生徒が選択されていません。ページを再読み込みしてください。'}
            return None, False, toast_data

        trigger_id = ctx.triggered_id

        updates = []

        if trigger_id == 'plan-empty-confirm-dialog':
            if not confirm_clicks:
                raise PreventUpdate
            books_to_unplan = list(current_progress.keys())
        else: # plan-save-btn
            all_selected_books = [id_dict['book'] for id_dict in book_ids]
            books_to_unplan = [book for book in (current_progress or {}).keys() if book not in all_selected_books]

        for book in books_to_unplan:
            level = next((lvl for lvl, b_list in get_master_textbook_list(subject).items() if book in b_list), "N/A")
            updates.append({'subject': subject, 'level': level, 'book_name': book, 'is_planned': False, 'completed_units': 0, 'total_units': 1, 'duration': None})

        if trigger_id != 'plan-empty-confirm-dialog':
            for i, id_dict in enumerate(book_ids):
                book_name = id_dict['book']
                val = progress_values[i] if progress_values and i < len(progress_values) else ""

                completed, total = 0, 1
                if val is None or val.strip() == "":
                    if current_progress and book_name in current_progress:
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

                duration = None
                if custom_books and book_name in custom_books:
                    duration = custom_books[book_name]['duration']

                updates.append({
                    'subject': subject, 'level': levels[i], 'book_name': book_name, 'is_planned': True,
                    'completed_units': completed, 'total_units': total if total > 0 else 1,
                    'duration': duration
                })

        if not updates and trigger_id != 'plan-empty-confirm-dialog':
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': '更新する内容がありません。', 'source': 'plan'}
            return None, False, toast_data

        success, message = add_or_update_student_progress(student_id, updates)

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': '学習計画を更新しました。', 'source': 'plan'}
            return None, False, toast_data
        else:
            return dbc.Alert(message, color="danger"), True, no_update