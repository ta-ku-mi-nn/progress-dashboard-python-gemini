# callbacks/past_exam_callbacks.py

from dash import Input, Output, State, html, no_update, callback_context, ALL, MATCH, dcc
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime, date, timedelta
import calendar # calendar をインポート

# --- 既存のimport ---
from data.nested_json_processor import (
    get_past_exam_results_for_student, add_past_exam_result,
    update_past_exam_result, delete_past_exam_result,
    add_acceptance_result,
    get_acceptance_results_for_student,
    update_acceptance_result,
    delete_acceptance_result
)
from charts.calendar_generator import create_html_calendar

def register_past_exam_callbacks(app):
    """過去問管理ページのコールバックを登録する"""

    # --- 過去問管理タブ関連のコールバック (変更なし) ---
    @app.callback(
        [Output('past-exam-modal', 'is_open'),
         Output('past-exam-modal-title', 'children'),
         Output('editing-past-exam-id-store', 'data'),
         Output('past-exam-date', 'date'),
         Output('past-exam-university', 'value'),
         Output('past-exam-faculty', 'value'),
         Output('past-exam-system', 'value'),
         Output('past-exam-year', 'value'),
         Output('past-exam-subject', 'value'),
         Output('past-exam-time', 'value'),
         Output('past-exam-correct', 'value'),
         Output('past-exam-total', 'value'),
         Output('past-exam-modal-alert', 'is_open')],
        [Input('open-past-exam-modal-btn', 'n_clicks'),
         Input({'type': 'edit-past-exam-btn', 'index': ALL}, 'n_clicks'),
         Input('cancel-past-exam-modal-btn', 'n_clicks')],
        [State('student-selection-store', 'data')],
        prevent_initial_call=True
    )
    def handle_modal_opening(add_clicks, edit_clicks, cancel_clicks, student_id):
        ctx = callback_context
        if not ctx.triggered or (isinstance(ctx.triggered_id, dict) and not ctx.triggered[0]['value']):
            raise PreventUpdate

        trigger_id = ctx.triggered_id

        if trigger_id == 'cancel-past-exam-modal-btn':
            return [False] + [no_update] * 12

        if trigger_id == 'open-past-exam-modal-btn':
            return True, "過去問結果の入力", None, date.today(), "", "", "", None, "", "", None, None, False

        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'edit-past-exam-btn':
            result_id = trigger_id['index']
            results = get_past_exam_results_for_student(student_id)
            result_to_edit = next((r for r in results if r['id'] == result_id), None)

            if result_to_edit:
                time_val = ""
                if result_to_edit.get('time_required') is not None:
                    time_val = str(result_to_edit['time_required'])
                    if result_to_edit.get('total_time_allowed') is not None:
                        time_val += f"/{result_to_edit['total_time_allowed']}"

                return (
                    True, "過去問結果の編集", result_id,
                    result_to_edit['date'], result_to_edit['university_name'],
                    result_to_edit.get('faculty_name', ''), result_to_edit.get('exam_system', ''),
                    result_to_edit['year'], result_to_edit['subject'],
                    time_val, result_to_edit.get('correct_answers'), result_to_edit.get('total_questions'),
                    False
                )
        return [no_update] * 13

    @app.callback(
        [Output('past-exam-modal-alert', 'children'),
         Output('past-exam-modal-alert', 'is_open', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True),
         Output('past-exam-modal', 'is_open', allow_duplicate=True)],
        [Input('save-past-exam-modal-btn', 'n_clicks')],
        [State('editing-past-exam-id-store', 'data'),
         State('student-selection-store', 'data'),
         State('past-exam-date', 'date'),
         State('past-exam-university', 'value'),
         State('past-exam-faculty', 'value'),
         State('past-exam-system', 'value'),
         State('past-exam-year', 'value'),
         State('past-exam-subject', 'value'),
         State('past-exam-time', 'value'),
         State('past-exam-correct', 'value'),
         State('past-exam-total', 'value')],
        prevent_initial_call=True
    )
    def save_past_exam_result(n_clicks, result_id, student_id, date, university, faculty, system, year, subject, time_str, correct, total):
        if not n_clicks or not student_id:
            raise PreventUpdate

        if not all([date, university, year, subject, total is not None]):
            return dbc.Alert("日付、大学名、年度、科目、問題数は必須です。", color="warning"), True, no_update, no_update

        time_required, total_time_allowed = None, None
        if time_str:
            try:
                if '/' in time_str:
                    parts = time_str.split('/')
                    time_required, total_time_allowed = int(parts[0]), int(parts[1])
                else:
                    time_required = int(time_str)
            except (ValueError, IndexError):
                return dbc.Alert("所要時間の形式が正しくありません。", color="warning"), True, no_update, no_update

        result_data = {
            'date': date, 'university_name': university, 'faculty_name': faculty,
            'exam_system': system, 'year': year, 'subject': subject,
            'time_required': time_required, 'total_time_allowed': total_time_allowed,
            'correct_answers': correct, 'total_questions': total
        }

        if result_id:
            success, message = update_past_exam_result(result_id, result_data)
        else:
            success, message = add_past_exam_result(student_id, result_data)

        if success:
            # ★★★ 過去問用の source を設定 ★★★
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'past_exam'}
            return "", False, toast_data, False
        else:
            return dbc.Alert(message, color="danger"), True, no_update, no_update

    @app.callback(
        [Output('delete-past-exam-confirm', 'displayed'),
         Output('editing-past-exam-id-store', 'data', allow_duplicate=True)],
        Input({'type': 'delete-past-exam-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def display_delete_confirmation(delete_clicks):
        ctx = callback_context
        if not ctx.triggered or not ctx.triggered[0]['value']:
            raise PreventUpdate

        result_id = ctx.triggered_id['index']
        return True, result_id

    @app.callback(
        Output('toast-trigger', 'data', allow_duplicate=True),
        Input('delete-past-exam-confirm', 'submit_n_clicks'),
        State('editing-past-exam-id-store', 'data'),
        prevent_initial_call=True
    )
    def execute_delete(n_clicks, result_id):
        if not n_clicks or not result_id:
            raise PreventUpdate

        success, message = delete_past_exam_result(result_id)
        # ★★★ 過去問用の source を設定 ★★★
        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'past_exam'}
        return toast_data

    @app.callback(
        [Output('past-exam-table-container', 'children'),
         Output('past-exam-university-filter', 'options'),
         Output('past-exam-subject-filter', 'options')],
        [Input('student-selection-store', 'data'),
         Input('toast-trigger', 'data'),
         Input('past-exam-university-filter', 'value'),
         Input('past-exam-subject-filter', 'value')],
    )
    def update_past_exam_table(student_id, toast_data, selected_university, selected_subject):
        ctx = callback_context
        # ★★★ source をチェックするように変更 ★★★
        if ctx.triggered_id == 'toast-trigger' and toast_data:
            if toast_data.get('source') != 'past_exam': # source が past_exam でなければ更新しない
                 raise PreventUpdate

        if not student_id:
            return dbc.Alert("まず生徒を選択してください。", color="info", className="mt-4"), [], []

        results = get_past_exam_results_for_student(student_id)
        df = pd.DataFrame(results) if results else pd.DataFrame()

        university_options = [{'label': u, 'value': u} for u in sorted(df['university_name'].unique())] if not df.empty else []
        subject_options = [{'label': s, 'value': s} for s in sorted(df['subject'].unique())] if not df.empty else []

        if df.empty:
            return dbc.Alert("この生徒の過去問結果はまだありません。", color="info", className="mt-4"), university_options, subject_options

        df_filtered = df.copy()
        if selected_university:
            df_filtered = df_filtered[df_filtered['university_name'] == selected_university]
        if selected_subject:
            df_filtered = df_filtered[df_filtered['subject'] == selected_subject]

        if df_filtered.empty:
             return dbc.Alert("フィルターに一致する過去問結果はありません。", color="warning", className="mt-4"), university_options, subject_options

        def calculate_percentage(row):
            correct, total = row['correct_answers'], row['total_questions']
            return f"{(correct / total * 100):.1f}%" if pd.notna(correct) and pd.notna(total) and total > 0 else ""
        df_filtered['正答率'] = df_filtered.apply(calculate_percentage, axis=1)

        def format_time(row):
            req, total = row['time_required'], row['total_time_allowed']
            if pd.notna(req) and pd.notna(total): return f"{int(req)}/{int(total)}"
            return f"{int(req)}" if pd.notna(req) else ""
        df_filtered['所要時間(分)'] = df_filtered.apply(format_time, axis=1)

        table_header = [html.Thead(html.Tr([
            html.Th("日付"), html.Th("大学名"), html.Th("学部名"),
            html.Th("入試方式"), html.Th("年度"), html.Th("科目"),
            html.Th("所要時間(分)"), html.Th("正答率"), html.Th("操作")
        ]))]

        table_body = []
        for _, row in df_filtered.iterrows():
            table_row = html.Tr([
                html.Td(row['date']),
                html.Td(row['university_name']),
                html.Td(row.get('faculty_name', '')),
                html.Td(row.get('exam_system', '')),
                html.Td(row['year']),
                html.Td(row['subject']),
                html.Td(row['所要時間(分)']),
                html.Td(row['正答率']),
                html.Td([
                    dbc.Button("編集", id={'type': 'edit-past-exam-btn', 'index': row['id']}, size="sm", className="me-1"),
                    dbc.Button("削除", id={'type': 'delete-past-exam-btn', 'index': row['id']}, color="danger", size="sm", outline=True)
                ])
            ])
            table_body.append(table_row)

        table = dbc.Table(table_header + [html.Tbody(table_body)], striped=True, bordered=True, hover=True, responsive=True)
        return table, university_options, subject_options


    # --- 大学合否タブ関連のコールバック ---

    @app.callback(
        [Output('acceptance-modal', 'is_open'),
         Output('acceptance-modal-title', 'children'),
         Output('editing-acceptance-id-store', 'data'),
         Output('acceptance-university', 'value'),
         Output('acceptance-faculty', 'value'),
         Output('acceptance-department', 'value'),
         Output('acceptance-system', 'value'),
         Output('acceptance-exam-date', 'date'),
         Output('acceptance-announcement-date', 'date'),
         Output('acceptance-modal-alert', 'is_open')],
        [Input('open-acceptance-modal-btn', 'n_clicks'),
         Input({'type': 'edit-acceptance-btn', 'index': ALL}, 'n_clicks'),
         Input('cancel-acceptance-modal-btn', 'n_clicks')],
        [State('student-selection-store', 'data')],
        prevent_initial_call=True
    )
    def handle_acceptance_modal_opening(add_clicks, edit_clicks, cancel_clicks, student_id):
        ctx = callback_context
        if not ctx.triggered or (isinstance(ctx.triggered_id, dict) and not ctx.triggered[0]['value']):
            raise PreventUpdate

        trigger_id = ctx.triggered_id

        if trigger_id == 'cancel-acceptance-modal-btn':
            return False, no_update, None, "", "", "", "", None, None, False

        if trigger_id == 'open-acceptance-modal-btn':
            return True, "大学合否結果の追加", None, "", "", "", "", None, None, False

        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'edit-acceptance-btn':
            result_id = trigger_id['index']
            results = get_acceptance_results_for_student(student_id)
            result_to_edit = next((r for r in results if r['id'] == result_id), None)

            if result_to_edit:
                exam_date = result_to_edit.get('exam_date')
                announcement_date = result_to_edit.get('announcement_date')
                try: exam_date = date.fromisoformat(exam_date) if exam_date else None
                except ValueError: exam_date = None
                try: announcement_date = date.fromisoformat(announcement_date) if announcement_date else None
                except ValueError: announcement_date = None

                return (
                    True, "大学合否結果の編集", result_id,
                    result_to_edit['university_name'], result_to_edit['faculty_name'],
                    result_to_edit.get('department_name', ''), result_to_edit.get('exam_system', ''),
                    exam_date,
                    announcement_date,
                    False
                )
        return False, no_update, None, "", "", "", "", None, None, False


    # 大学合否結果の保存 (日付フィールド追加 + カレンダー月更新 + source追加)
    @app.callback(
        [Output('acceptance-modal-alert', 'children'),
         Output('acceptance-modal-alert', 'is_open', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True),
         Output('acceptance-modal', 'is_open', allow_duplicate=True),
         Output('current-calendar-month-store', 'data', allow_duplicate=True)],
        [Input('save-acceptance-modal-btn', 'n_clicks')],
        [State('editing-acceptance-id-store', 'data'),
         State('student-selection-store', 'data'),
         State('acceptance-university', 'value'),
         State('acceptance-faculty', 'value'),
         State('acceptance-department', 'value'),
         State('acceptance-system', 'value'),
         State('acceptance-exam-date', 'date'),
         State('acceptance-announcement-date', 'date')
         ],
        prevent_initial_call=True
    )
    def save_acceptance_result(n_clicks, result_id, student_id, university, faculty, department, system, exam_date, announcement_date):
        if not n_clicks or not student_id:
            raise PreventUpdate

        if not university or not faculty:
            return dbc.Alert("大学名と学部名は必須です。", color="warning"), True, no_update, no_update, no_update

        result_data = {
            'university_name': university, 'faculty_name': faculty,
            'department_name': department, 'exam_system': system,
            'exam_date': exam_date,
            'announcement_date': announcement_date
        }

        target_month_str = no_update
        if exam_date:
            try:
                target_month_str = datetime.strptime(exam_date, '%Y-%m-%d').strftime('%Y-%m')
            except ValueError: pass
        elif announcement_date:
             try:
                target_month_str = datetime.strptime(announcement_date, '%Y-%m-%d').strftime('%Y-%m')
             except ValueError: pass

        if result_id:
            success, message = update_acceptance_result(result_id, result_data)
        else:
            result_data['result'] = None
            success, message = add_acceptance_result(student_id, result_data)

        if success:
            toast_message = message.replace("大学合否結果", f"'{university} {faculty}' の合否結果")
            # ★★★ source を 'acceptance' に設定 ★★★
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': toast_message, 'source': 'acceptance'}
            return "", False, toast_data, False, target_month_str
        else:
            return dbc.Alert(message, color="danger"), True, no_update, no_update, no_update


    @app.callback(
        [Output('delete-acceptance-confirm', 'displayed'),
         Output('editing-acceptance-id-store', 'data', allow_duplicate=True)],
        Input({'type': 'delete-acceptance-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def display_acceptance_delete_confirmation(delete_clicks):
        ctx = callback_context
        if not ctx.triggered or not ctx.triggered[0]['value']:
            raise PreventUpdate

        result_id = ctx.triggered_id['index']
        return True, result_id

    # 大学合否 削除の実行 (source追加)
    @app.callback(
        Output('toast-trigger', 'data', allow_duplicate=True),
        Input('delete-acceptance-confirm', 'submit_n_clicks'),
        State('editing-acceptance-id-store', 'data'),
        prevent_initial_call=True
    )
    def execute_acceptance_delete(n_clicks, result_id):
        if not n_clicks or not result_id:
            raise PreventUpdate

        success, message = delete_acceptance_result(result_id)
        # ★★★ source を 'acceptance' に設定 ★★★
        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'acceptance'}
        return toast_data


    # 大学合否テーブルの描画と更新 (sourceチェックに変更)
    @app.callback(
        Output('acceptance-table-container', 'children'),
        [Input('student-selection-store', 'data'),
         Input('toast-trigger', 'data')]
    )
    def update_acceptance_table(student_id, toast_data):
        ctx = callback_context
        # ★★★ source をチェックするように変更 ★★★
        if ctx.triggered_id == 'toast-trigger' and toast_data:
            if toast_data.get('source') != 'acceptance': # source が acceptance でなければ更新しない
                 raise PreventUpdate

        if not student_id:
            return [] # 空リストを返すように修正

        results = get_acceptance_results_for_student(student_id)
        if not results:
            return dbc.Alert("この生徒の大学合否結果はまだありません。", color="info", className="mt-4")

        table_header = [
            html.Thead(html.Tr([
                html.Th("大学名"), html.Th("学部名"), html.Th("学科名"),
                html.Th("受験方式"), html.Th("受験日"), html.Th("発表日"),
                html.Th("合否", style={'width': '150px'}),
                html.Th("操作", style={'width': '120px'})
            ]))
        ]

        table_body = []
        for r in results:
            result_id = r['id']
            row = html.Tr([
                html.Td(r['university_name']),
                html.Td(r['faculty_name']),
                html.Td(r.get('department_name', '')),
                html.Td(r.get('exam_system', '')),
                html.Td(r.get('exam_date', '')),
                html.Td(r.get('announcement_date', '')),
                html.Td(
                    dcc.Dropdown(
                        id={'type': 'acceptance-result-dropdown', 'index': result_id},
                        options=[
                            {'label': '未選択', 'value': ''},
                            {'label': '合格', 'value': '合格'},
                            {'label': '不合格', 'value': '不合格'}
                        ],
                        value=r.get('result') if r.get('result') is not None else '',
                        clearable=False,
                        style={'minWidth': '100px'}
                    )
                ),
                html.Td([
                    dbc.Button("編集", id={'type': 'edit-acceptance-btn', 'index': result_id}, size="sm", className="me-1"),
                    dbc.Button("削除", id={'type': 'delete-acceptance-btn', 'index': result_id}, color="danger", size="sm", outline=True)
                ])
            ])
            table_body.append(row)

        return dbc.Table(table_header + [html.Tbody(table_body)], striped=True, bordered=True, hover=True, responsive=True)


    # 合否ドロップダウンの変更をDBに反映 (source追加)
    @app.callback(
        Output('toast-trigger', 'data', allow_duplicate=True),
        Input({'type': 'acceptance-result-dropdown', 'index': ALL}, 'value'),
        State({'type': 'acceptance-result-dropdown', 'index': ALL}, 'id'),
        State('student-selection-store', 'data'),
        prevent_initial_call=True
    )
    def update_acceptance_status_dropdown(dropdown_values, dropdown_ids, student_id):
        ctx = callback_context
        if not ctx.triggered_id:
            raise PreventUpdate

        triggered_id_dict = ctx.triggered_id
        result_id = triggered_id_dict['index']
        new_result = ctx.triggered[0]['value']

        success, message = update_acceptance_result(result_id, {'result': new_result})

        if success:
            if student_id:
                results = get_acceptance_results_for_student(student_id)
                updated_record = next((r for r in results if r['id'] == result_id), None)
                if updated_record:
                     status_text = new_result if new_result else "未選択"
                     message = f"'{updated_record['university_name']} {updated_record['faculty_name']}' の合否を '{status_text}' に更新しました。"
                else:
                     message = "合否情報を更新しました。"
            else:
                 message = "合否情報を更新しました。"
        else:
             message = f"合否情報の更新に失敗しました: {message}"

        # ★★★ source を 'acceptance' に設定 ★★★
        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'acceptance'}
        return toast_data


    # --- 大学合否カレンダーの更新 (sourceチェックに変更) ---
    @app.callback(
        Output('acceptance-calendar-container', 'children'),
        [Input('student-selection-store', 'data'),
         Input('toast-trigger', 'data'),
         Input('current-calendar-month-store', 'data')],
        State('past-exam-tabs', 'active_tab')
    )
    def update_acceptance_calendar(student_id, toast_data, target_month, active_tab):
        ctx = callback_context

        if active_tab != 'tab-gantt':
            raise PreventUpdate

        # ★★★ source をチェックするように変更 ★★★
        if ctx.triggered_id == 'toast-trigger' and toast_data:
            if toast_data.get('source') != 'acceptance': # source が acceptance でなければ更新しない
                 raise PreventUpdate

        if not target_month:
            target_month = date.today().strftime('%Y-%m')

        if not student_id:
            calendar_html = create_html_calendar([], target_month)
            return calendar_html

        acceptance_data = get_acceptance_results_for_student(student_id)
        calendar_html = create_html_calendar(acceptance_data, target_month)
        return calendar_html

    # --- カレンダー年月更新関連 (変更なし) ---
    @app.callback(
        Output('current-calendar-month-store', 'data', allow_duplicate=True),
        [Input('prev-month-btn', 'n_clicks'),
         Input('next-month-btn', 'n_clicks'),
         Input('past-exam-tabs', 'active_tab')],
        State('current-calendar-month-store', 'data'),
        prevent_initial_call=True
    )
    def update_calendar_month(prev_clicks, next_clicks, active_tab, current_month_str):
        ctx = callback_context
        trigger_id = ctx.triggered_id

        if trigger_id == 'past-exam-tabs' and active_tab == 'tab-gantt':
            if current_month_str:
                 return no_update
            else:
                 return date.today().strftime('%Y-%m')

        if trigger_id not in ['prev-month-btn', 'next-month-btn']:
             raise PreventUpdate

        if not current_month_str:
            current_month_str = date.today().strftime('%Y-%m')

        try:
            current_month = datetime.strptime(current_month_str, '%Y-%m').date()
        except (ValueError, TypeError):
            current_month = date.today()

        if trigger_id == 'prev-month-btn':
            first_day_current_month = current_month.replace(day=1)
            last_day_prev_month = first_day_current_month - timedelta(days=1)
            new_month = last_day_prev_month.replace(day=1)
            return new_month.strftime('%Y-%m')
        elif trigger_id == 'next-month-btn':
            days_in_month = calendar.monthrange(current_month.year, current_month.month)[1]
            first_day_next_month = current_month.replace(day=1) + timedelta(days=days_in_month)
            return first_day_next_month.strftime('%Y-%m')

        raise PreventUpdate


    @app.callback(
        Output('current-month-display', 'children'),
        Input('current-calendar-month-store', 'data')
    )
    def display_current_month(month_str):
        if not month_str:
            month_str = date.today().strftime('%Y-%m')
        try:
            dt = datetime.strptime(month_str, '%Y-%m')
            return f"{dt.year}年 {dt.month}月"
        except (ValueError, TypeError):
            today = date.today()
            return f"{today.year}年 {today.month}月"