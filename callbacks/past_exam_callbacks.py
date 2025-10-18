# callbacks/past_exam_callbacks.py

from dash import Input, Output, State, html, no_update, callback_context, ALL, MATCH, dcc
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime, date, timedelta
import calendar

# --- 既存のimport ---
from data.nested_json_processor import (
    get_past_exam_results_for_student, add_past_exam_result,
    update_past_exam_result, delete_past_exam_result,
    add_acceptance_result,
    get_acceptance_results_for_student,  # これを使用
    update_acceptance_result,
    delete_acceptance_result
)
from charts.calendar_generator import create_html_calendar

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
    # 日付文字列をdatetimeオブジェクトに変換（不正な形式は無視）
    df['app_deadline_dt'] = pd.to_datetime(df['application_deadline'], errors='coerce').dt.date # ★追加
    df['exam_dt'] = pd.to_datetime(df['exam_date'], errors='coerce').dt.date
    df['announcement_dt'] = pd.to_datetime(df['announcement_date'], errors='coerce').dt.date
    df['proc_deadline_dt'] = pd.to_datetime(df['procedure_deadline'], errors='coerce').dt.date # ★追加

    # --- ★ここからロジック変更★ ---
    # 今日以降の「出願期日」をリストアップ
    future_app_deadlines = []
    if 'app_deadline_dt' in df.columns:
        future_app_deadlines = df[df['app_deadline_dt'] >= today]['app_deadline_dt'].dropna().tolist()

    # 今日以降の出願期日があれば、最も近いものを返す
    if future_app_deadlines:
        nearest_date = min(future_app_deadlines)
        return nearest_date.strftime('%Y-%m')

    # 出願期日がない場合、他の今日以降の日付をリストアップ
    future_other_dates = []
    if 'exam_dt' in df.columns:
        future_other_dates.extend(df[df['exam_dt'] >= today]['exam_dt'].dropna().tolist())
    if 'announcement_dt' in df.columns:
        future_other_dates.extend(df[df['announcement_dt'] >= today]['announcement_dt'].dropna().tolist())
    if 'proc_deadline_dt' in df.columns:
         future_other_dates.extend(df[df['proc_deadline_dt'] >= today]['proc_deadline_dt'].dropna().tolist())

    # 他の日付があれば、最も近いものを返す
    if future_other_dates:
        nearest_date = min(future_other_dates)
        return nearest_date.strftime('%Y-%m')
    # --- ★ここまでロジック変更★ ---

    # 未来の日付が全くない場合は当月
    return today.strftime('%Y-%m')
# --- ★★★ ここまで修正 ★★★ ---

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
        [Input('student-selection-store', 'data'), Input('toast-trigger', 'data'),
         Input('past-exam-university-filter', 'value'), Input('past-exam-subject-filter', 'value'),
         Input('refresh-past-exam-table-btn', 'n_clicks')],
    )
    def update_past_exam_table(student_id, toast_data, selected_university, selected_subject, refresh_clicks): # 引数に refresh_clicks を追加
        ctx = callback_context
        # toast_trigger または refresh_button が押された時のみ処理を進めるか、
        # student_id, filter が変更された時も更新する
        triggered_id = ctx.triggered_id if ctx.triggered_id else 'initial load' # 初期ロード対応

        # toast 由来で source が違う場合 or 更新ボタンでも n_clicks が None の場合は早期リターン
        if triggered_id == 'toast-trigger':
            if not toast_data or toast_data.get('source') != 'past_exam':
                raise PreventUpdate
        elif triggered_id == 'refresh-past-exam-table-btn' and refresh_clicks is None:
             raise PreventUpdate

        if not student_id:
            alert_message = dbc.Alert("まず生徒を選択してください。", color="info", className="mt-4")
            return alert_message, [], [] # アラートと空のリスト2つを返す


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

# --- save_acceptance_result 関数 ---
    @app.callback(
        [Output('acceptance-modal-alert', 'children'),
         Output('acceptance-modal-alert', 'is_open', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True),
         Output('acceptance-modal', 'is_open', allow_duplicate=True),
         Output('current-calendar-month-store', 'data', allow_duplicate=True)],
        [Input('save-acceptance-modal-btn', 'n_clicks')],
        [State('editing-acceptance-id-store', 'data'), State('student-selection-store', 'data'),
         State('acceptance-university', 'value'), State('acceptance-faculty', 'value'),
         State('acceptance-department', 'value'), State('acceptance-system', 'value'),
         State('acceptance-application-deadline', 'date'), # ★追加
         State('acceptance-exam-date', 'date'),
         State('acceptance-announcement-date', 'date'),
         State('acceptance-procedure-deadline', 'date')], # ★追加
        prevent_initial_call=True
    )
    def save_acceptance_result(n_clicks, result_id, student_id, university, faculty, department, system,
                             app_deadline, exam_date, announcement_date, proc_deadline): # ★引数追加
        if not n_clicks or not student_id: raise PreventUpdate
        if not university or not faculty: return dbc.Alert("大学名と学部名は必須です。", color="warning"), True, no_update, no_update, no_update
        result_data = {'university_name': university, 'faculty_name': faculty, 'department_name': department, 'exam_system': system,
                       'application_deadline': app_deadline, # ★追加
                       'exam_date': exam_date,
                       'announcement_date': announcement_date,
                       'procedure_deadline': proc_deadline} # ★追加

        target_month_str = no_update
        # カレンダー表示月の決定ロジック (出願期日も考慮)
        date_candidates = [d for d in [app_deadline, exam_date, announcement_date, proc_deadline] if d]
        if date_candidates:
            try:
                # 最も早い日付を基準にする
                earliest_date = min(date_candidates)
                target_month_str = datetime.strptime(earliest_date, '%Y-%m-%d').strftime('%Y-%m')
            except ValueError: pass

        if result_id: success, message = update_acceptance_result(result_id, result_data)
        else: result_data['result'] = None; success, message = add_acceptance_result(student_id, result_data)

        if success:
            toast_message = message.replace("大学合否結果", f"'{university} {faculty}' の合否結果")
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': toast_message, 'source': 'acceptance'}
            return "", False, toast_data, False, target_month_str
        else: return dbc.Alert(message, color="danger"), True, no_update, no_update, no_update

    # --- update_acceptance_table 関数 ---
    @app.callback(
        Output('acceptance-table-container', 'children'),
        [Input('student-selection-store', 'data'), Input('toast-trigger', 'data'),
         Input('refresh-acceptance-table-btn', 'n_clicks')]
    )
    def update_acceptance_table(student_id, toast_data, refresh_clicks): # 引数に refresh_clicks を追加
        ctx = callback_context
        triggered_id = ctx.triggered_id if ctx.triggered_id else 'initial load'

        # toast 由来で source が違う場合 or 更新ボタンでも n_clicks が None の場合は早期リターン
        if triggered_id == 'toast-trigger':
            if not toast_data or toast_data.get('source') != 'acceptance':
                 raise PreventUpdate
        elif triggered_id == 'refresh-acceptance-table-btn' and refresh_clicks is None:
             raise PreventUpdate

        if not student_id:
             return [] # dbc.Alert("まず生徒を選択してください。", color="info", className="mt-4") # レイアウトに合わせて変更

    @app.callback(
        [Output('delete-acceptance-confirm', 'displayed'),
         Output('editing-acceptance-id-store', 'data', allow_duplicate=True)],
        Input({'type': 'delete-acceptance-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def display_acceptance_delete_confirmation(delete_clicks):
        ctx = callback_context
        if not ctx.triggered or not ctx.triggered[0]['value']: raise PreventUpdate
        result_id = ctx.triggered_id['index']; return True, result_id

    @app.callback(
        Output('toast-trigger', 'data', allow_duplicate=True),
        Input('delete-acceptance-confirm', 'submit_n_clicks'),
        State('editing-acceptance-id-store', 'data'),
        prevent_initial_call=True
    )
    def execute_acceptance_delete(n_clicks, result_id):
        if not n_clicks or not result_id: raise PreventUpdate
        success, message = delete_acceptance_result(result_id)
        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'acceptance'}
        return toast_data

    @app.callback(
        Output('toast-trigger', 'data', allow_duplicate=True),
        Input({'type': 'acceptance-result-dropdown', 'index': ALL}, 'value'),
        State({'type': 'acceptance-result-dropdown', 'index': ALL}, 'id'),
        State('student-selection-store', 'data'),
        prevent_initial_call=True
    )
    def update_acceptance_status_dropdown(dropdown_values, dropdown_ids, student_id):
        ctx = callback_context
        if not ctx.triggered_id: raise PreventUpdate
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
                else: message = "合否情報を更新しました。"
            else: message = "合否情報を更新しました。"
        else: message = f"合否情報の更新に失敗しました: {message}"
        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'acceptance'}
        return toast_data


    # --- 大学合否カレンダーの更新 ---
    @app.callback(
        Output('acceptance-calendar-container', 'children'),
        [Input('student-selection-store', 'data'), Input('toast-trigger', 'data'),
         Input('current-calendar-month-store', 'data'), Input('refresh-calendar-btn', 'n_clicks')],
        State('past-exam-tabs', 'active_tab')
    )
    def update_acceptance_calendar(student_id, toast_data, target_month, refresh_clicks, active_tab): # 引数に refresh_clicks を追加
        ctx = callback_context
        triggered_id = ctx.triggered_id if ctx.triggered_id else 'initial load'

        # カレンダータブ以外 or toast の source が違う or 更新ボタンで n_clicks が None の場合早期リターン
        if active_tab != 'tab-gantt': raise PreventUpdate
        if triggered_id == 'toast-trigger':
            if not toast_data or toast_data.get('source') != 'acceptance': raise PreventUpdate
        elif triggered_id == 'refresh-calendar-btn' and refresh_clicks is None:
             raise PreventUpdate

        if not target_month: target_month = date.today().strftime('%Y-%m')
        if not student_id: return create_html_calendar([], target_month)
        acceptance_data = get_acceptance_results_for_student(student_id)
        calendar_html = create_html_calendar(acceptance_data, target_month)
        return calendar_html

    # カレンダーの表示年月を更新するコールバック
    @app.callback(
        Output('current-calendar-month-store', 'data'), # allow_duplicate=True を削除
        [Input('prev-month-btn', 'n_clicks'), Input('next-month-btn', 'n_clicks'), Input('past-exam-tabs', 'active_tab')],
        [State('current-calendar-month-store', 'data'),
         # ★★★ Stateを追加 ★★★
         State('student-selection-store', 'data')],
        prevent_initial_call=True
    )
    def update_calendar_month(prev_clicks, next_clicks, active_tab, current_month_str, student_id): # student_id を追加
        ctx = callback_context
        trigger_id = ctx.triggered_id

        # カレンダータブがアクティブになった時
        if trigger_id == 'past-exam-tabs' and active_tab == 'tab-gantt':
            if current_month_str: # 既に月が設定されていれば（例：保存直後など）、それを維持
                 return no_update
            else: # まだ月が設定されていない場合
                 if student_id:
                     # ★★★ 生徒の合否データを取得して最も近い未来の月を計算 ★★★
                     acceptance_data = get_acceptance_results_for_student(student_id)
                     return find_nearest_future_month(acceptance_data)
                 else:
                     # 生徒が選択されていない場合は当月
                     return date.today().strftime('%Y-%m')

        # 前月/次月ボタンが押された場合のみ処理
        if trigger_id not in ['prev-month-btn', 'next-month-btn']:
             raise PreventUpdate

        # current_month_str がない場合は当月を基準にする (念のため)
        if not current_month_str:
            current_month_str = date.today().strftime('%Y-%m')

        try: current_month = datetime.strptime(current_month_str, '%Y-%m').date()
        except (ValueError, TypeError): current_month = date.today()

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
        if not month_str: month_str = date.today().strftime('%Y-%m')
        try: dt = datetime.strptime(month_str, '%Y-%m'); return f"{dt.year}年 {dt.month}月"
        except (ValueError, TypeError): today = date.today(); return f"{today.year}年 {today.month}月"