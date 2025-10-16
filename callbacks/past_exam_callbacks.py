# callbacks/past_exam_callbacks.py

from dash import Input, Output, State, html, no_update, callback_context, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime, date

from data.nested_json_processor import (
    get_past_exam_results_for_student, add_past_exam_result,
    update_past_exam_result, delete_past_exam_result
)

def register_past_exam_callbacks(app):
    """過去問管理ページのコールバックを登録する"""

    # モーダルを開く処理（新規追加と編集の両方に対応）
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

        # キャンセルボタンで閉じる
        if trigger_id == 'cancel-past-exam-modal-btn':
            return [False] + [no_update] * 12

        # 新規追加ボタンで開く（フォームをリセット）
        if trigger_id == 'open-past-exam-modal-btn':
            return True, "過去問結果の入力", None, date.today(), "", "", "", None, "", "", None, None, False

        # 編集ボタンで開く（フォームにデータを読み込む）
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

    # 結果の保存（新規と更新の両方に対応）
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

        if not all([date, university, year, subject, total]):
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

        if result_id:  # IDがあれば更新、なければ新規作成
            success, message = update_past_exam_result(result_id, result_data)
        else:
            success, message = add_past_exam_result(student_id, result_data)

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': message}
            return "", False, toast_data, False
        else:
            return dbc.Alert(message, color="danger"), True, no_update, no_update

    # 削除確認ダイアログの表示
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

    # 削除の実行
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
        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message}
        return toast_data

    # テーブルの描画
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
        if not student_id:
            return dbc.Alert("まず生徒を選択してください。", color="info", className="mt-4"), [], []

        results = get_past_exam_results_for_student(student_id)

        df = pd.DataFrame(results) if results else pd.DataFrame()

        university_options = [{'label': u, 'value': u} for u in sorted(df['university_name'].unique())] if not df.empty else []
        subject_options = [{'label': s, 'value': s} for s in sorted(df['subject'].unique())] if not df.empty else []

        if df.empty:
            return dbc.Alert("この生徒の過去問結果はまだありません。", color="info", className="mt-4"), [], []

        if selected_university:
            df = df[df['university_name'] == selected_university]
        if selected_subject:
            df = df[df['subject'] == selected_subject]

        def calculate_percentage(row):
            correct, total = row['correct_answers'], row['total_questions']
            return f"{(correct / total * 100):.1f}%" if pd.notna(correct) and pd.notna(total) and total > 0 else ""
        df['正答率'] = df.apply(calculate_percentage, axis=1)

        def format_time(row):
            req, total = row['time_required'], row['total_time_allowed']
            if pd.notna(total): return f"{int(req)}/{int(total)}"
            return f"{int(req)}" if pd.notna(req) else ""
        df['所要時間(分)'] = df.apply(format_time, axis=1)

        df['操作'] = df.apply(lambda row: html.Div([
            dbc.Button("編集", id={'type': 'edit-past-exam-btn', 'index': row['id']}, size="sm", className="me-1"),
            dbc.Button("削除", id={'type': 'delete-past-exam-btn', 'index': row['id']}, color="danger", size="sm", outline=True)
        ]), axis=1)

        table_df = df[['date', 'university_name', 'faculty_name', 'exam_system', 'year', 'subject', '所要時間(分)', '正答率', '操作']]
        table_df.columns = ['日付', '大学名', '学部名', '入試方式', '年度', '科目', '所要時間(分)', '正答率', '操作']

        table = dbc.Table.from_dataframe(table_df, striped=True, bordered=True, hover=True, responsive=True)
        return table, university_options, subject_options