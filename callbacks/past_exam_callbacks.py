# callbacks/past_exam_callbacks.py

from dash import Input, Output, State, html, no_update, callback_context, ALL, MATCH, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime, date

from data.nested_json_processor import (
    get_past_exam_results_for_student, add_past_exam_result,
    update_past_exam_result, delete_past_exam_result,
    add_acceptance_result, get_acceptance_results_for_student,
    update_acceptance_result, delete_acceptance_result
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
    
    # 大学合否モーダルを開く処理
    @app.callback(
        [Output('acceptance-modal', 'is_open'),
         Output('acceptance-modal-title', 'children'),
         Output('editing-acceptance-id-store', 'data'),
         Output('acceptance-university', 'value'),
         Output('acceptance-faculty', 'value'),
         Output('acceptance-department', 'value'),
         Output('acceptance-system', 'value'),
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
            return False, no_update, None, "", "", "", "", False

        if trigger_id == 'open-acceptance-modal-btn':
            return True, "大学合否結果の追加", None, "", "", "", "", False

        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'edit-acceptance-btn':
            result_id = trigger_id['index']
            results = get_acceptance_results_for_student(student_id)
            result_to_edit = next((r for r in results if r['id'] == result_id), None)

            if result_to_edit:
                return (
                    True, "大学合否結果の編集", result_id,
                    result_to_edit['university_name'], result_to_edit['faculty_name'],
                    result_to_edit.get('department_name', ''), result_to_edit.get('exam_system', ''),
                    False
                )
        return False, no_update, None, "", "", "", "", False # デフォルトは閉じる


    # 大学合否結果の保存
    @app.callback(
        [Output('acceptance-modal-alert', 'children'),
         Output('acceptance-modal-alert', 'is_open', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True),
         Output('acceptance-modal', 'is_open', allow_duplicate=True)],
        [Input('save-acceptance-modal-btn', 'n_clicks')],
        [State('editing-acceptance-id-store', 'data'),
         State('student-selection-store', 'data'),
         State('acceptance-university', 'value'),
         State('acceptance-faculty', 'value'),
         State('acceptance-department', 'value'),
         State('acceptance-system', 'value')],
        prevent_initial_call=True
    )
    def save_acceptance_result(n_clicks, result_id, student_id, university, faculty, department, system):
        if not n_clicks or not student_id:
            raise PreventUpdate

        if not university or not faculty:
            return dbc.Alert("大学名と学部名は必須です。", color="warning"), True, no_update, no_update

        result_data = {
            'university_name': university, 'faculty_name': faculty,
            'department_name': department, 'exam_system': system
        }

        if result_id:  # 更新
            success, message = update_acceptance_result(result_id, result_data)
        else: # 新規追加
            success, message = add_acceptance_result(student_id, result_data)

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': message}
            return "", False, toast_data, False
        else:
            return dbc.Alert(message, color="danger"), True, no_update, no_update


    # 大学合否 削除確認ダイアログの表示
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

    # 大学合否 削除の実行
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
        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message}
        return toast_data


    # 大学合否テーブルの描画と更新
    @app.callback(
        Output('acceptance-table-container', 'children'),
        [Input('student-selection-store', 'data'),
         Input('toast-trigger', 'data')] # 保存・削除後に再描画
    )
    def update_acceptance_table(student_id, toast_data):
        ctx = callback_context
        # toast_triggerがトリガーだが、今回の更新と関係ないトーストなら更新しない
        if ctx.triggered_id == 'toast-trigger' and toast_data:
            # 関係するメッセージかを判定 (より具体的に判定した方が良い場合もある)
            if "大学合否結果" not in toast_data.get('message', ''):
                 raise PreventUpdate

        if not student_id:
            return []

        results = get_acceptance_results_for_student(student_id)
        if not results:
            return dbc.Alert("この生徒の大学合否結果はまだありません。", color="info", className="mt-4")

        table_data = []
        for r in results:
            # ★★★ ここから修正 ★★★
            # 操作ボタンをMarkdown形式の文字列として生成
            edit_button = f'<button id=\'{{"type":"edit-acceptance-btn", "index":{r["id"]}}}\' class="btn btn-sm btn-secondary me-1">編集</button>'
            delete_button = f'<button id=\'{{"type":"delete-acceptance-btn", "index":{r["id"]}}}\' class="btn btn-sm btn-outline-danger">削除</button>'
            # ★★★ ここまで修正 ★★★

            table_data.append({
                'id': r['id'],
                '大学名': r['university_name'],
                '学部名': r['faculty_name'],
                '学科名': r.get('department_name', ''),
                '受験方式': r.get('exam_system', ''),
                '合否': r.get('result', ''), # DBにNULLなら空文字
                '操作': f'{edit_button}{delete_button}' # ボタン文字列を追加
            })

        table = dash_table.DataTable(
            id='acceptance-table',
            columns=[
                {'name': '大学名', 'id': '大学名', 'editable': False},
                {'name': '学部名', 'id': '学部名', 'editable': False},
                {'name': '学科名', 'id': '学科名', 'editable': False},
                {'name': '受験方式', 'id': '受験方式', 'editable': False},
                {'name': '合否', 'id': '合否', 'presentation': 'dropdown'},
                {'name': '操作', 'id': '操作', 'presentation': 'markdown', 'editable': False} # Markdownとしてボタンを表示
            ],
            data=table_data, # ★★★ 修正: ボタンを含むデータを渡す ★★★
            editable=True,
            dropdown={
                 '合否': {
                     'options': [
                         {'label': '未選択', 'value': ''},
                         {'label': '合格', 'value': '合格'},
                         {'label': '不合格', 'value': '不合格'}
                     ],
                     'clearable': False # 未選択に戻せないようにする場合 Trueにする
                 }
             },
            row_deletable=False,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'minWidth': '100px', 'whiteSpace': 'normal', 'height': 'auto'},
            markdown_options={"html": True}, # HTMLタグを許可
             data_previous=table_data # 変更検知用
        )


        return table

    # 合否ドロップダウンの変更をDBに反映
    @app.callback(
        Output('toast-trigger', 'data', allow_duplicate=True),
        Input('acceptance-table', 'data'),
        State('acceptance-table', 'data_previous'),
        prevent_initial_call=True
    )
    def update_acceptance_status_in_db(current_data, previous_data):
        if current_data is None or previous_data is None:
            raise PreventUpdate

        changed_rows = []
        # データ行数が変わった場合（追加/削除操作）はこのコールバックでは処理しない
        if len(current_data) != len(previous_data):
             raise PreventUpdate

        # どの行のどのセルが変わったか特定
        for i in range(len(current_data)):
             # 合否列だけチェック
             if current_data[i].get('合否') != previous_data[i].get('合否'):
                 changed_rows.append({
                     'id': current_data[i]['id'],
                     'result': current_data[i].get('合否')
                 })

        if not changed_rows:
            raise PreventUpdate

        # 変更があった行についてDBを更新
        update_success_count = 0
        update_fail_count = 0
        error_msg = ""

        for row in changed_rows:
            success, message = update_acceptance_result(row['id'], {'result': row['result']})
            if success:
                update_success_count += 1
            else:
                update_fail_count += 1
                error_msg = message # 最後のエラーメッセージを保持

        if update_fail_count > 0:
            message = f"{update_success_count}件成功、{update_fail_count}件失敗しました。エラー: {error_msg}"
        else:
             message = f"{update_success_count}件の合否情報を更新しました。"

        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message}
        return toast_data