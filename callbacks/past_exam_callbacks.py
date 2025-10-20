# callbacks/past_exam_callbacks.py

from dash import Input, Output, State, html, no_update, callback_context, ALL, MATCH, dcc
from dash import clientside_callback
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
from dateutil.relativedelta import relativedelta

# --- 既存のimport ---
from data.nested_json_processor import (
    get_past_exam_results_for_student, add_past_exam_result,
    update_past_exam_result, delete_past_exam_result,
    add_acceptance_result,
    get_acceptance_results_for_student,  # これを使用
    update_acceptance_result,
    delete_acceptance_result
)
from charts.calendar_generator import create_html_calendar, create_single_month_table

# --- find_nearest_future_month 関数を復活 ---
def find_nearest_future_month(acceptance_data):
    """
    合否データの中から、今日以降で最も近い「出願期日」の年月('YYYY-MM')を返す。
    該当する出願期日がない場合は、他の未来の日付（受験日、発表日、手続期日）で最も近い月を返し、
    それらもない場合は現在の年月を返す。
    """
    today = date.today()
    nearest_date = None

    if not acceptance_data:
        return today.strftime('%Y-%m')

    df = pd.DataFrame(acceptance_data)
    df['app_deadline_dt'] = pd.to_datetime(df.get('application_deadline'), errors='coerce').dt.date
    df['exam_dt'] = pd.to_datetime(df.get('exam_date'), errors='coerce').dt.date
    df['announcement_dt'] = pd.to_datetime(df.get('announcement_date'), errors='coerce').dt.date
    df['proc_deadline_dt'] = pd.to_datetime(df.get('procedure_deadline'), errors='coerce').dt.date

    future_app_deadlines = df[df['app_deadline_dt'] >= today]['app_deadline_dt'].dropna().tolist()
    if future_app_deadlines:
        nearest_date = min(future_app_deadlines)
        return nearest_date.strftime('%Y-%m')

    future_other_dates = []
    future_other_dates.extend(df[df['exam_dt'] >= today]['exam_dt'].dropna().tolist())
    future_other_dates.extend(df[df['announcement_dt'] >= today]['announcement_dt'].dropna().tolist())
    future_other_dates.extend(df[df['proc_deadline_dt'] >= today]['proc_deadline_dt'].dropna().tolist())

    if future_other_dates:
        nearest_date = min(future_other_dates)
        return nearest_date.strftime('%Y-%m')

    return today.strftime('%Y-%m')
# --- ここまで復活 ---

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
                return (True, "過去問結果の編集", result_id, result_to_edit['date'], result_to_edit['university_name'],
                        result_to_edit.get('faculty_name', ''), result_to_edit.get('exam_system', ''),
                        result_to_edit['year'], result_to_edit['subject'],
                        time_val, result_to_edit.get('correct_answers'), result_to_edit.get('total_questions'), False)
        return [no_update] * 13

    @app.callback(
        [Output('past-exam-modal-alert', 'children'),
         Output('past-exam-modal-alert', 'is_open', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True),
         Output('past-exam-modal', 'is_open', allow_duplicate=True)],
        [Input('save-past-exam-modal-btn', 'n_clicks')],
        [State('editing-past-exam-id-store', 'data'),
         State('student-selection-store', 'data'),
         State('past-exam-date', 'date'), State('past-exam-university', 'value'),
         State('past-exam-faculty', 'value'), State('past-exam-system', 'value'),
         State('past-exam-year', 'value'), State('past-exam-subject', 'value'),
         State('past-exam-time', 'value'), State('past-exam-correct', 'value'),
         State('past-exam-total', 'value')],
        prevent_initial_call=True
    )
    def save_past_exam_result(n_clicks, result_id, student_id, date_val, university, faculty, system, year, subject, time_str, correct, total):
        if not n_clicks or not student_id: raise PreventUpdate
        if not all([date_val, university, year, subject, total is not None]):
            return dbc.Alert("日付、大学名、年度、科目、問題数は必須です。", color="warning"), True, no_update, no_update
        time_required, total_time_allowed = None, None
        if time_str:
            try:
                if '/' in time_str:
                    parts = time_str.split('/'); time_required, total_time_allowed = int(parts[0]), int(parts[1])
                else: time_required = int(time_str)
            except (ValueError, IndexError):
                return dbc.Alert("所要時間の形式が正しくありません。", color="warning"), True, no_update, no_update
        result_data = {'date': date_val, 'university_name': university, 'faculty_name': faculty, 'exam_system': system, 'year': year, 'subject': subject,
                       'time_required': time_required, 'total_time_allowed': total_time_allowed, 'correct_answers': correct, 'total_questions': total}
        if result_id: success, message = update_past_exam_result(result_id, result_data)
        else: success, message = add_past_exam_result(student_id, result_data)
        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'past_exam'}
            return "", False, toast_data, False
        else: return dbc.Alert(message, color="danger"), True, no_update, no_update

    @app.callback(
        [Output('delete-past-exam-confirm', 'displayed'),
         Output('editing-past-exam-id-store', 'data', allow_duplicate=True)],
        Input({'type': 'delete-past-exam-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def display_delete_confirmation(delete_clicks):
        ctx = callback_context
        if not ctx.triggered or not ctx.triggered[0]['value']: raise PreventUpdate
        result_id = ctx.triggered_id['index']; return True, result_id

    @app.callback(
        Output('toast-trigger', 'data', allow_duplicate=True),
        Input('delete-past-exam-confirm', 'submit_n_clicks'),
        State('editing-past-exam-id-store', 'data'),
        prevent_initial_call=True
    )
    def execute_delete(n_clicks, result_id):
        if not n_clicks or not result_id: raise PreventUpdate
        success, message = delete_past_exam_result(result_id)
        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'past_exam'}
        return toast_data

    @app.callback(
        [Output('past-exam-table-container', 'children'),
         Output('past-exam-university-filter', 'options'),
         Output('past-exam-subject-filter', 'options')],
        [Input('student-selection-store', 'data'),
         Input('toast-trigger', 'data'),
         Input('past-exam-university-filter', 'value'),
         Input('past-exam-subject-filter', 'value'),
         Input('refresh-past-exam-table-btn', 'n_clicks')]
    )
    def update_past_exam_table(student_id, toast_data, selected_university, selected_subject, refresh_clicks):
        ctx = callback_context
        triggered_id = ctx.triggered_id if ctx.triggered_id else 'initial load'

        # PreventUpdate の条件チェック
        if triggered_id == 'toast-trigger':
            if not toast_data or toast_data.get('source') != 'past_exam':
                raise PreventUpdate
        elif triggered_id == 'refresh-past-exam-table-btn' and refresh_clicks is None:
             raise PreventUpdate

        # --- ここから戻り値を確実に返すための構造 ---
        table_content = None
        university_options = []
        subject_options = []

        if not student_id:
            table_content = dbc.Alert("まず生徒を選択してください。", color="info", className="mt-4")
            # この時点で戻り値を確定させる
            return table_content, university_options, subject_options

        try: # データ取得と処理中のエラーをキャッチ（念のため）
            results = get_past_exam_results_for_student(student_id)
            df = pd.DataFrame(results) if results else pd.DataFrame()

            if df.empty:
                table_content = dbc.Alert("この生徒の過去問結果はまだありません。", color="info", className="mt-4")
                # university_options と subject_options は空リストのまま
            else:
                # オプション生成
                university_options = [{'label': u, 'value': u} for u in sorted(df['university_name'].unique())]
                subject_options = [{'label': s, 'value': s} for s in sorted(df['subject'].unique())]

                # フィルター処理
                df_filtered = df.copy()
                if selected_university:
                    df_filtered = df_filtered[df_filtered['university_name'] == selected_university]
                if selected_subject:
                    df_filtered = df_filtered[df_filtered['subject'] == selected_subject]

                if df_filtered.empty:
                    table_content = dbc.Alert("フィルターに一致する過去問結果はありません。", color="warning", className="mt-4")
                    # オプションはフィルター前のものを維持
                else:
                    # テーブル生成ロジック (変更なし)
                    def calculate_percentage(row):
                        correct, total = row['correct_answers'], row['total_questions']
                        return f"{(correct / total * 100):.1f}%" if pd.notna(correct) and pd.notna(total) and total > 0 else ""
                    df_filtered['正答率'] = df_filtered.apply(calculate_percentage, axis=1)
                    def format_time(row):
                        req, total = row['time_required'], row['total_time_allowed']
                        if pd.notna(req) and pd.notna(total): return f"{int(req)}/{int(total)}"
                        return f"{int(req)}" if pd.notna(req) else ""
                    df_filtered['所要時間(分)'] = df_filtered.apply(format_time, axis=1)
                    table_header = [html.Thead(html.Tr([html.Th("日付"), html.Th("大学名"), html.Th("学部名"), html.Th("入試方式"), html.Th("年度"), html.Th("科目"),
                                                        html.Th("所要時間(分)"), html.Th("正答率"), html.Th("操作")]))]
                    table_body = [html.Tbody([html.Tr([html.Td(row['date']), html.Td(row['university_name']), html.Td(row.get('faculty_name', '')),
                                                        html.Td(row.get('exam_system', '')), html.Td(row['year']), html.Td(row['subject']),
                                                        html.Td(row['所要時間(分)']), html.Td(row['正答率']),
                                                        html.Td([dbc.Button("編集", id={'type': 'edit-past-exam-btn', 'index': row['id']}, size="sm", className="me-1"),
                                                                 dbc.Button("削除", id={'type': 'delete-past-exam-btn', 'index': row['id']}, color="danger", size="sm", outline=True)])
                                                      ]) for _, row in df_filtered.iterrows()])]
                    table_content = dbc.Table(table_header + table_body, striped=True, bordered=True, hover=True, responsive=True)

        except Exception as e:
            print(f"Error in update_past_exam_table: {e}") # エラーログ出力
            table_content = dbc.Alert(f"テーブル表示中にエラーが発生しました: {e}", color="danger")
            # エラー発生時も空のオプションを返す

        # --- 必ず3つの要素を返す ---
        return table_content, university_options, subject_options


    # --- 大学合否タブ関連のコールバック ---

    @app.callback(
        [Output('acceptance-modal', 'is_open'),
         Output('acceptance-modal-title', 'children'),
         Output('editing-acceptance-id-store', 'data'),
         Output('acceptance-university', 'value'), Output('acceptance-faculty', 'value'),
         Output('acceptance-department', 'value'), Output('acceptance-system', 'value'),
         Output('acceptance-application-deadline', 'date'),
         Output('acceptance-exam-date', 'date'), Output('acceptance-announcement-date', 'date'),
         Output('acceptance-procedure-deadline', 'date'),
         Output('acceptance-modal-alert', 'is_open')],
        [Input('open-acceptance-modal-btn', 'n_clicks'), Input({'type': 'edit-acceptance-btn', 'index': ALL}, 'n_clicks'),
         Input('cancel-acceptance-modal-btn', 'n_clicks')],
        [State('student-selection-store', 'data')],
        prevent_initial_call=True
    )
    def handle_acceptance_modal_opening(add_clicks, edit_clicks, cancel_clicks, student_id):
        ctx = callback_context
        if not ctx.triggered or (isinstance(ctx.triggered_id, dict) and not ctx.triggered[0]['value']): raise PreventUpdate
        trigger_id = ctx.triggered_id
        if trigger_id == 'cancel-acceptance-modal-btn': return False, no_update, None, "", "", "", "", None, None, None, None, False
        if trigger_id == 'open-acceptance-modal-btn': return True, "大学合否結果の追加", None, "", "", "", "", None, None, None, None, False
        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'edit-acceptance-btn':
            result_id = trigger_id['index']
            results = get_acceptance_results_for_student(student_id)
            result_to_edit = next((r for r in results if r['id'] == result_id), None)
            if result_to_edit:
                # 日付変換関数を定義
                def parse_date(date_str):
                    try: return date.fromisoformat(date_str) if date_str else None
                    except ValueError: return None

                app_deadline = parse_date(result_to_edit.get('application_deadline')) # ★追加
                exam_date = parse_date(result_to_edit.get('exam_date'))
                announcement_date = parse_date(result_to_edit.get('announcement_date'))
                proc_deadline = parse_date(result_to_edit.get('procedure_deadline')) # ★追加

                # ★戻り値に期日を追加
                return (True, "大学合否結果の編集", result_id, result_to_edit['university_name'], result_to_edit['faculty_name'],
                        result_to_edit.get('department_name', ''), result_to_edit.get('exam_system', ''),
                        app_deadline, exam_date, announcement_date, proc_deadline, False)
        # ★出力変数が2つ増えたので no_update の数を調整
        return False, no_update, None, "", "", "", "", None, None, None, None, False

# --- save_acceptance_result コールバックの修正 ---
    @app.callback(
        [Output('acceptance-modal-alert', 'children'),
         Output('acceptance-modal-alert', 'is_open', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True),
         Output('acceptance-modal', 'is_open', allow_duplicate=True),
         Output('current-calendar-month-store', 'data', allow_duplicate=True)], # ★ StoreへのOutput復活
        [Input('save-acceptance-modal-btn', 'n_clicks')],
        [State('editing-acceptance-id-store', 'data'), State('student-selection-store', 'data'),
         State('acceptance-university', 'value'), State('acceptance-faculty', 'value'),
         State('acceptance-department', 'value'), State('acceptance-system', 'value'),
         State('acceptance-application-deadline', 'date'),
         State('acceptance-exam-date', 'date'),
         State('acceptance-announcement-date', 'date'),
         State('acceptance-procedure-deadline', 'date')],
        prevent_initial_call=True
    )
    def save_acceptance_result(n_clicks, result_id, student_id, university, faculty, department, system,
                             app_deadline, exam_date, announcement_date, proc_deadline):
        if not n_clicks or not student_id: raise PreventUpdate
        if not university or not faculty: return dbc.Alert("大学名と学部名は必須です。", color="warning"), True, no_update, no_update, no_update
        result_data = {'university_name': university, 'faculty_name': faculty, 'department_name': department, 'exam_system': system,
                       'application_deadline': app_deadline, 'exam_date': exam_date,
                       'announcement_date': announcement_date, 'procedure_deadline': proc_deadline}

        # ★ カレンダー表示月の決定ロジックを復活
        target_month_str = no_update
        date_candidates = [d for d in [app_deadline, exam_date, announcement_date, proc_deadline] if d]
        if date_candidates:
            try:
                # ISOフォーマットの日付文字列からdatetime.dateオブジェクトに変換して比較
                earliest_date_obj = min([date.fromisoformat(d_str) for d_str in date_candidates])
                target_month_str = earliest_date_obj.strftime('%Y-%m')
            except (ValueError, TypeError): pass # 不正な日付フォーマットは無視

        if result_id: success, message = update_acceptance_result(result_id, result_data)
        else: result_data['result'] = None; success, message = add_acceptance_result(student_id, result_data)

        if success:
            toast_message = message.replace("大学合否結果", f"'{university} {faculty}' の合否結果")
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': toast_message, 'source': 'acceptance'}
            # ★ target_month_str を返すように修正
            return "", False, toast_data, False, target_month_str
        else: return dbc.Alert(message, color="danger"), True, no_update, no_update, no_update

    # --- 合否ステータス更新コールバック (変更なし) ---
    @app.callback(
        Output('toast-trigger', 'data', allow_duplicate=True),
        Input({'type': 'acceptance-result-dropdown', 'index': ALL}, 'value'),
        State({'type': 'acceptance-result-dropdown', 'index': ALL}, 'id'),
        State('student-selection-store', 'data'),
        prevent_initial_call=True
    )
    def update_acceptance_status_dropdown(dropdown_values, dropdown_ids, student_id):
        # ... (内容は変更なし) ...
        ctx = callback_context
        if not ctx.triggered_id: raise PreventUpdate
        triggered_id_dict = ctx.triggered_id
        result_id = triggered_id_dict['index']
        new_result = ctx.triggered[0]['value']
        success, message = update_acceptance_result(result_id, {'result': new_result if new_result else None}) # 空文字列をNoneに
        if success:
            if student_id:
                results = get_acceptance_results_for_student(student_id)
                updated_record = next((r for r in results if r['id'] == result_id), None)
                if updated_record:
                     status_text = new_result if new_result else "未選択"
                     message = f"'{updated_record['university_name']} {updated_record['faculty_name']}' の合否を '{status_text}' に更新しました。"
                else: message = "合否情報を更新しました。"
            else: message = "合否情報を更新しました。"
        else: message = f"合否情報の更新に失敗しました: {message}"
        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'acceptance'}
        return toast_data


    # --- Web表示用カレンダーの更新 ---
    @app.callback(
        Output('web-calendar-container', 'children'), # ★ Output ID を変更
        [Input('student-selection-store', 'data'),
         Input('toast-trigger', 'data'),
         Input('current-calendar-month-store', 'data'), # ★ Input を復活
         Input('refresh-calendar-btn', 'n_clicks')],
        State('past-exam-tabs', 'active_tab')
    )
    def update_acceptance_calendar(student_id, toast_data, target_month, refresh_clicks, active_tab): # ★ target_month 引数を復活
        ctx = callback_context
        triggered_id = ctx.triggered_id if ctx.triggered_id else 'initial load'

        if active_tab != 'tab-gantt': raise PreventUpdate
        if triggered_id == 'toast-trigger':
            if not toast_data or toast_data.get('source') != 'acceptance': raise PreventUpdate
        elif triggered_id == 'refresh-calendar-btn' and refresh_clicks is None:
             raise PreventUpdate
        # target_monthがない場合、find_nearest_future_monthを呼び出すロジックは update_calendar_month に移譲

        if not target_month: # 初回表示などでtarget_monthがない場合
             if student_id:
                 acceptance_data_for_init = get_acceptance_results_for_student(student_id)
                 target_month = find_nearest_future_month(acceptance_data_for_init)
             else:
                 target_month = date.today().strftime('%Y-%m') # 生徒未選択なら当月

        if not student_id:
             # 空のデータで単月カレンダー生成
            return create_html_calendar([], target_month)

        acceptance_data = get_acceptance_results_for_student(student_id)
        # 単月カレンダー生成関数を呼び出す
        calendar_html = create_html_calendar(acceptance_data, target_month)
        return calendar_html

    # --- ★ カレンダーの表示年月を更新するコールバック (復活) ★ ---
    @app.callback(
        Output('current-calendar-month-store', 'data'),
        [Input('prev-month-btn', 'n_clicks'),
         Input('next-month-btn', 'n_clicks'),
         Input('past-exam-tabs', 'active_tab'),
         Input('student-selection-store', 'data')], # ★ 生徒変更もトリガーに追加
        [State('current-calendar-month-store', 'data')],
        prevent_initial_call=True
    )
    def update_calendar_month(prev_clicks, next_clicks, active_tab, student_id, current_month_str):
        ctx = callback_context
        trigger_id = ctx.triggered_id

        # カレンダータブ以外 or 生徒未選択なら更新しない
        if active_tab != 'tab-gantt' or not student_id:
             raise PreventUpdate

        # タブ切り替え時 or 生徒変更時
        if trigger_id in ['past-exam-tabs', 'student-selection-store']:
            # ★ 生徒の合否データを取得して最も近い未来の月 or 当月を計算 ★
            acceptance_data = get_acceptance_results_for_student(student_id)
            return find_nearest_future_month(acceptance_data)

        # 前月/次月ボタンが押された場合のみ処理
        if trigger_id not in ['prev-month-btn', 'next-month-btn']:
             raise PreventUpdate

        if not current_month_str:
            current_month_str = date.today().strftime('%Y-%m')

        try: current_month = datetime.strptime(current_month_str, '%Y-%m').date()
        except (ValueError, TypeError): current_month = date.today()

        if trigger_id == 'prev-month-btn':
            new_month = (current_month.replace(day=1) - timedelta(days=1)).replace(day=1)
            return new_month.strftime('%Y-%m')
        elif trigger_id == 'next-month-btn':
            days_in_month = calendar.monthrange(current_month.year, current_month.month)[1]
            new_month = current_month.replace(day=1) + timedelta(days=days_in_month)
            return new_month.strftime('%Y-%m')

        raise PreventUpdate

    # --- ★ 現在の年月を表示するコールバック (復活) ★ ---
    @app.callback(
        Output('current-month-display', 'children'),
        Input('current-calendar-month-store', 'data')
    )
    def display_current_month(month_str):
        # 初回など month_str が None の場合があるためデフォルトを設定
        if not month_str:
             month_str = date.today().strftime('%Y-%m') # デフォルトを当月に
        try:
             dt = datetime.strptime(month_str, '%Y-%m')
             return f"{dt.year}年 {dt.month}月"
        except (ValueError, TypeError):
             # month_str が不正な場合も当月を表示
             today = date.today()
             return f"{today.year}年 {today.month}月"

    # --- ★ 印刷用カレンダーエリアを更新するコールバック (新規追加) ★ ---
    @app.callback(
        Output('printable-calendar-area', 'children'),
        [Input('student-selection-store', 'data'),
         Input('toast-trigger', 'data')], # データ更新時にも再生成
        prevent_initial_call=True
    )
    def update_printable_calendar(student_id, toast_data):
        ctx = callback_context
        triggered_id = ctx.triggered_id if ctx.triggered_id else 'initial load'

        # toastトリガーの場合、sourceをチェック
        if triggered_id == 'toast-trigger':
            if not toast_data or toast_data.get('source') != 'acceptance':
                raise PreventUpdate
        # student_idがない場合は空にする
        elif not student_id:
            return []

        acceptance_data = get_acceptance_results_for_student(student_id)
        if not acceptance_data:
            return [dbc.Alert("印刷対象の受験・合否データがありません。", color="info")]

        # --- データの存在する最初の月と最後の月を決定 ---
        df = pd.DataFrame(acceptance_data)
        all_dates = []
        date_cols = ['application_deadline', 'exam_date', 'announcement_date', 'procedure_deadline']
        for col in date_cols:
             if col in df.columns:
                 # to_datetime でエラーを無視し、NaTでないものをリストに追加
                 valid_dates = pd.to_datetime(df[col], errors='coerce').dropna().tolist()
                 all_dates.extend(valid_dates)

        if not all_dates:
            return [dbc.Alert("有効な日付データがありません。", color="warning")]

        min_date = min(all_dates).date().replace(day=1)
        max_date = max(all_dates).date().replace(day=1)

        # --- 必要な月のテーブルを生成 ---
        printable_tables = []
        current_month_loop = min_date
        # DataFrame を再ソート (create_single_month_table内でのソートは非効率なため)
        sort_keys_print = []
        if 'app_deadline_dt' in df.columns: sort_keys_print.append('app_deadline_dt')
        if 'exam_dt' in df.columns: sort_keys_print.append('exam_dt')
        sort_keys_print.extend(['university_name', 'faculty_name'])
        # dfの日付列を再生成（必要なら）
        dt_cols_print = ['app_deadline_dt', 'exam_dt', 'announcement_dt', 'proc_deadline_dt']
        for col, dt_col in zip(date_cols, dt_cols_print):
            if col in df.columns: df[dt_col] = pd.to_datetime(df[col], errors='coerce')
            else: df[dt_col] = pd.NaT
        df_all_sorted_print = df.sort_values(by=sort_keys_print, ascending=True, na_position='last') if sort_keys_print and not df.empty else df

        while current_month_loop <= max_date:
            year, month = current_month_loop.year, current_month_loop.month
            # create_single_month_table にソート済みDataFrameを渡す
            printable_tables.append(create_single_month_table(df_all_sorted_print, year, month))
            current_month_loop += relativedelta(months=+1)

        return printable_tables

    # --- 印刷用clientside_callback (変更なし) ---
    clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks > 0) {
                // printable-only クラスを持つ要素を表示し、
                // printable-hide クラスを持つ要素を非表示にするスタイルを一時的に適用
                const style = document.createElement('style');
                style.innerHTML = `
                    @media print {
                        .printable-only { display: block !important; }
                        .printable-hide { display: none !important; }
                        /* 必要に応じて他の印刷専用スタイルもここに追加 */
                        body, #page-content { background-color: white !important; }
                        #printable-calendar-area .single-month-wrapper { page-break-inside: avoid !important; }
                        #printable-calendar-area .calendar-table { page-break-inside: avoid !important; table-layout: fixed !important; font-size: 7pt !important;}
                        #printable-calendar-area .calendar-table th, #printable-calendar-area .calendar-table td { height: 22px !important; padding: 2px !important; border: 1px solid #ccc !important; }
                        #printable-calendar-area .calendar-info-header-cell, #printable-calendar-area .calendar-info-cell { width: 80px !important; font-size: 6pt !important; background-color: #f8f9fa !important; vertical-align: top !important;}
                        #printable-calendar-area .calendar-info-header-cell { background-color: #e9ecef !important; vertical-align: middle !important;}
                        #printable-calendar-area .calendar-header-cell, #printable-calendar-area .calendar-date-cell { width: auto !important; min-width: 0 !important; font-size: 7pt !important; }
                        #printable-calendar-area .calendar-header-cell { font-size: 6pt !important; }
                        #printable-calendar-area .calendar-table th br { display: block !important; }
                        #printable-calendar-area .saturday { background-color: #f0f8ff !important; } /* 背景色も !important */
                        #printable-calendar-area .sunday { background-color: #fff7f0 !important; }
                        #printable-calendar-area .app-deadline-cell { background-color: #ffff7f !important; }
                        #printable-calendar-area .exam-date-cell { background-color: #ff7f7f !important; }
                        #printable-calendar-area .announcement-date-cell { background-color: #7fff7f !important; }
                        #printable-calendar-area .proc-deadline-cell { background-color: #bf7fff !important; }
                        @page { size: A4 portrait; margin: 10mm; }
                    }
                `;
                document.head.appendChild(style);

                setTimeout(function() {
                    window.print();
                    // 印刷ダイアログが閉じた後にスタイルを削除
                    setTimeout(() => {
                         document.head.removeChild(style);
                    }, 500); // 印刷ダイアログが閉じるのを待つ時間
                }, 500); // スタイルの適用とレンダリング待ち
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('print-calendar-btn', 'n_clicks', allow_duplicate=True),
        Input('print-calendar-btn', 'n_clicks'),
        prevent_initial_call=True
    )