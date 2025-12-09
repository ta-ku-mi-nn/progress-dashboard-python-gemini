# callbacks/past_exam_callbacks.py

from dash import Input, Output, State, html, no_update, callback_context, ALL, MATCH, dcc
from dash import clientside_callback
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime, date, timedelta # date, timedelta をインポート
import calendar
from dateutil.relativedelta import relativedelta
import math # isnan チェック用
import json

# --- 必要な関数をインポート ---
from data.nested_json_processor import (
    get_past_exam_results_for_student, add_past_exam_result,
    update_past_exam_result, delete_past_exam_result,
    add_acceptance_result,
    get_acceptance_results_for_student,
    update_acceptance_result,
    delete_acceptance_result,
    # ★★★ 模試結果関連の関数を追加 ★★★
    add_mock_exam_result,
    get_mock_exam_results_for_student,
    update_mock_exam_result,
    delete_mock_exam_result
)
from charts.calendar_generator import create_html_calendar, create_single_month_table

# --- find_nearest_future_month 関数 (変更なし) ---
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

    # Ensure acceptance_data is a list of dictionaries if it's not already
    if isinstance(acceptance_data, pd.DataFrame):
        acceptance_list = acceptance_data.to_dict('records')
    elif isinstance(acceptance_data, list):
        acceptance_list = acceptance_data
    else:
        return today.strftime('%Y-%m') # Or handle error appropriately

    df = pd.DataFrame(acceptance_list)

    # Convert date columns safely
    date_cols_map = {
        'application_deadline': 'app_deadline_dt',
        'exam_date': 'exam_dt',
        'announcement_date': 'announcement_dt',
        'procedure_deadline': 'proc_deadline_dt'
    }
    for col, dt_col in date_cols_map.items():
        if col in df.columns:
            # Convert potential date objects to strings first if necessary
            df[col] = df[col].apply(lambda x: x.isoformat() if isinstance(x, date) else x)
            df[dt_col] = pd.to_datetime(df[col], errors='coerce').dt.date
        else:
            df[dt_col] = pd.NaT # Ensure the column exists even if empty

    # --- Find nearest future application deadline ---
    # Ensure 'app_deadline_dt' exists before filtering
    if 'app_deadline_dt' in df.columns:
        future_app_deadlines_series = df.loc[df['app_deadline_dt'].notna() & (df['app_deadline_dt'] >= today), 'app_deadline_dt']
        future_app_deadlines = future_app_deadlines_series.tolist()
        if future_app_deadlines:
            nearest_date = min(future_app_deadlines)
            return nearest_date.strftime('%Y-%m')

    # --- Find nearest future other dates ---
    future_other_dates = []
    for dt_col in ['exam_dt', 'announcement_dt', 'proc_deadline_dt']:
        if dt_col in df.columns:
             future_dates_series = df.loc[df[dt_col].notna() & (df[dt_col] >= today), dt_col]
             future_other_dates.extend(future_dates_series.tolist())

    if future_other_dates:
        nearest_date = min(future_other_dates)
        return nearest_date.strftime('%Y-%m')

    # --- Default to current month ---
    return today.strftime('%Y-%m')

# --- _create_mock_exam_table ヘルパー関数 (変更なし) ---
def _create_mock_exam_table(df, table_type, student_id):
    """マークまたは記述の模試結果DataFrameからdbc.Tableを生成する"""
    if df.empty:
        type_jp = "マーク" if table_type == "mark" else "記述"
        return dbc.Alert(f"登録されている{type_jp}模試の結果はありません。", color="info", className="mt-3")

    # 表示するカラムを選択
    base_cols = ['id', 'result_type', 'mock_exam_name', 'mock_exam_format', 'grade', 'round', 'exam_date']
    score_col_style = {'width': '60px', 'textAlign': 'center'} 

    if table_type == "mark":
        score_cols = [
            'subject_kokugo_mark', 'subject_math1a_mark', 'subject_math2bc_mark',
            'subject_english_r_mark', 'subject_english_l_mark', 'subject_rika1_mark', 'subject_rika2_mark',
            'subject_shakai1_mark', 'subject_shakai2_mark', 'subject_rika_kiso1_mark',
            'subject_rika_kiso2_mark', 'subject_info_mark'
        ]
        col_headers_jp = ["国", "数IA", "数IIBC", "英R", "英L", "理①", "理②", "社①", "社②", "理基①", "理基②", "情報"]
    else: # descriptive
        score_cols = [
            'subject_kokugo_desc', 'subject_math_desc', 'subject_english_desc',
            'subject_rika1_desc', 'subject_rika2_desc', 'subject_shakai1_desc', 'subject_shakai2_desc'
        ]
        col_headers_jp = ["国", "数", "英", "理①", "理②", "社①", "社②"]

    display_cols = base_cols[:6] + ['exam_date'] + score_cols
    for col in display_cols:
        if col not in df.columns:
            df[col] = None 

    df_display = df[display_cols].copy()

    # ヘッダー生成
    header_cells = [
        html.Th("種類"), html.Th("模試名"), html.Th("形式"), html.Th("学年"), html.Th("回"), html.Th("受験日")
    ] + [html.Th(jp, style=score_col_style) for jp in col_headers_jp] + [html.Th("操作", style={'width': '100px'})]
    table_header = [html.Thead(html.Tr(header_cells))]

    # ボディ生成
    table_body_rows = []
    for _, row in df_display.iterrows():
        cells = [
            html.Td(row['result_type']),
            html.Td(row['mock_exam_name']),
            html.Td(row['mock_exam_format']),
            html.Td(row['grade']),
            html.Td(row['round']),
            html.Td(row['exam_date'].strftime('%Y-%m-%d') if pd.notna(row['exam_date']) and isinstance(row['exam_date'], date) else '-'),
        ]
        # ★★★ 修正点: 点数を文字列として処理し、None/NaNはハイフンにする ★★★
        for col in score_cols:
            score = row[col]
            if pd.isna(score):
                display_score = '-'
            else:
                # 整数に変換してから文字列化、もしくはそのまま文字列化
                try:
                    display_score = str(int(score))
                except:
                    display_score = str(score)
            
            cells.append(html.Td(display_score, style=score_col_style))

        # 操作ボタンを追加
        cells.append(html.Td([
            dbc.Button("編集", id={'type': 'edit-mock-exam-btn', 'index': row['id']}, size="sm", className="me-1"),
            dbc.Button("削除", id={'type': 'delete-mock-exam-trigger-btn', 'index': row['id']}, color="danger", size="sm", outline=True)
        ]))
        table_body_rows.append(html.Tr(cells))

    table_body = [html.Tbody(table_body_rows)]
    return dbc.Table(table_header + table_body, striped=True, bordered=True, hover=True, responsive=True, size="sm")

def register_past_exam_callbacks(app):
    """過去問管理、入試管理、模試結果ページのコールバックを登録する"""

    # --- 過去問管理タブ関連のコールバック ---
    # (handle_past_exam_modal_opening - 変更なし)
    @app.callback(
        [Output('past-exam-modal', 'is_open'),
         Output('past-exam-modal-title', 'children'),
         Output('editing-past-exam-id-store', 'data'), # 削除用にIDを保持
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
    def handle_past_exam_modal_opening(add_clicks, edit_clicks_list, cancel_clicks, student_id):
        ctx = callback_context
        triggered_id_str = ctx.triggered_id if isinstance(ctx.triggered_id, str) else json.dumps(ctx.triggered_id)

        # どのボタンも押されていない、または edit ボタンで n_clicks が 0 の場合
        if not ctx.triggered or (isinstance(ctx.triggered_id, dict) and not ctx.triggered[0]['value']):
            raise PreventUpdate

        trigger_id = ctx.triggered_id

        # キャンセルボタン
        if trigger_id == 'cancel-past-exam-modal-btn':
            return False, no_update, None, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, False

        # 新規追加ボタン
        if trigger_id == 'open-past-exam-modal-btn':
            return True, "過去問結果の入力", None, date.today(), "", "", "", None, "", "", None, None, False

        # 編集ボタン (パターンマッチング)
        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'edit-past-exam-btn':
            if not student_id: raise PreventUpdate # 生徒が選択されていない場合
            result_id = trigger_id['index']
            results = get_past_exam_results_for_student(student_id)
            result_to_edit = next((r for r in results if r['id'] == result_id), None)

            if result_to_edit:
                # 日付オブジェクトをYYYY-MM-DD文字列に変換
                date_val = result_to_edit['date'].isoformat() if isinstance(result_to_edit['date'], date) else None

                # 時間表示の整形
                time_val = ""
                req = result_to_edit.get('time_required')
                total_allowed = result_to_edit.get('total_time_allowed')
                if req is not None:
                    time_val = str(int(req)) # 整数に変換して文字列化
                    if total_allowed is not None:
                        time_val += f"/{int(total_allowed)}" # 整数に変換して文字列化

                return (True, "過去問結果の編集", result_id, date_val, result_to_edit.get('university_name', ''),
                        result_to_edit.get('faculty_name', ''), result_to_edit.get('exam_system', ''),
                        result_to_edit.get('year'), result_to_edit.get('subject', ''),
                        time_val, result_to_edit.get('correct_answers'), result_to_edit.get('total_questions'), False)

        # 上記以外の場合はモーダルを閉じるか、状態を維持
        return False, no_update, None, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, False

    # (save_past_exam_result - 変更なし)
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
        # 必須項目チェック
        required_fields = {'date': date_val, 'university_name': university, 'year': year, 'subject': subject, 'total_questions': total}
        missing_fields = [k for k, v in required_fields.items() if not v and v != 0] # total=0は有効とする
        if missing_fields:
            field_names_jp = {'date': '日付', 'university_name': '大学名', 'year': '年度', 'subject': '科目', 'total_questions': '問題数'}
            missing_jp = [field_names_jp.get(f, f) for f in missing_fields]
            return dbc.Alert(f"{'、'.join(missing_jp)} は必須です。", color="warning"), True, no_update, no_update

        # 時間のパース
        time_required, total_time_allowed = None, None
        if time_str:
            try:
                parts = str(time_str).split('/')
                if len(parts) == 1 and parts[0].strip():
                    time_required = int(parts[0].strip())
                elif len(parts) == 2 and parts[0].strip() and parts[1].strip():
                    time_required = int(parts[0].strip())
                    total_time_allowed = int(parts[1].strip())
                # 空文字列や "/" のみの場合は None のまま
            except (ValueError, TypeError):
                return dbc.Alert("所要時間の形式が正しくありません (例: 60 または 60/80)。", color="warning"), True, no_update, no_update

        # correct, total が空文字列の場合 None に変換
        correct_val = int(correct) if correct is not None and str(correct).strip() != '' else None
        total_val = int(total) if total is not None and str(total).strip() != '' else None # total は必須なので通常ここには来ないはずだが念のため

        result_data = {'date': date_val, 'university_name': university, 'faculty_name': faculty or None, 'exam_system': system or None, 'year': year, 'subject': subject,
                       'time_required': time_required, 'total_time_allowed': total_time_allowed, 'correct_answers': correct_val, 'total_questions': total_val}

        if result_id: success, message = update_past_exam_result(result_id, result_data)
        else: success, message = add_past_exam_result(student_id, result_data)

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'past_exam'}
            return "", False, toast_data, False
        else: return dbc.Alert(message, color="danger"), True, no_update, no_update

    # ★★★ 修正箇所 (display_delete_past_exam_confirmation) ★★★
    @app.callback(
        Output('delete-past-exam-confirm', 'displayed'),
        Input({'type': 'delete-past-exam-btn', 'index': ALL}, 'n_clicks'), # モーダル内の削除ボタン
        State('editing-past-exam-id-store', 'data'), # モーダルを開いたときのIDを使う
        prevent_initial_call=True
    )
    def display_delete_past_exam_confirmation(delete_clicks, result_id):
        ctx = callback_context # ★ コンテキスト取得
        # ★ トリガーがない、またはトリガーの値がfalsy (None, 0) の場合は中断
        if not ctx.triggered or not ctx.triggered[0]['value']:
             raise PreventUpdate
        # ★ State の ID もチェック
        if result_id is None:
            raise PreventUpdate
            
        return True
    # ★★★ 修正ここまで ★★★

    # (execute_past_exam_delete - 変更なし)
    @app.callback(
        [Output('toast-trigger', 'data', allow_duplicate=True),
         Output('past-exam-modal', 'is_open', allow_duplicate=True), # 削除後にモーダルを閉じる
         Output('editing-past-exam-id-store', 'data', allow_duplicate=True)], # IDをクリア
        Input('delete-past-exam-confirm', 'submit_n_clicks'),
        State('editing-past-exam-id-store', 'data'),
        prevent_initial_call=True
    )
    def execute_past_exam_delete(submit_n_clicks, result_id):
        if not submit_n_clicks or result_id is None:
            raise PreventUpdate
        success, message = delete_past_exam_result(result_id)
        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'past_exam'}
        # 成功したらモーダルを閉じ、IDストアをクリア
        return toast_data, not success, None if success else no_update

    # (update_past_exam_table - 変更なし、前回の修正を維持)
    @app.callback(
        [Output('past-exam-table-container', 'children'),
         Output('past-exam-university-filter', 'options'),
         Output('past-exam-subject-filter', 'options')],
        [Input('student-selection-store', 'data'),
         Input('toast-trigger', 'data'),
         Input('past-exam-university-filter', 'value'),
         Input('past-exam-subject-filter', 'value'),
         Input('refresh-past-exam-table-btn', 'n_clicks'),
         Input('past-exam-tabs', 'active_tab')], # ★ Input として active_tab
    )
    def update_past_exam_table(student_id, toast_data, selected_university, selected_subject, refresh_clicks, active_tab):
        ctx = callback_context
        triggered_id = ctx.triggered_id if ctx.triggered_id else 'initial load'

        # ★ 過去問タブが表示されていない場合は更新しない
        if active_tab != 'tab-past-exam':
            raise PreventUpdate

        # PreventUpdate の条件チェック
        if triggered_id == 'toast-trigger':
            if not toast_data or toast_data.get('source') != 'past_exam':
                raise PreventUpdate
        elif triggered_id == 'refresh-past-exam-table-btn' and refresh_clicks is None:
             raise PreventUpdate
        # ★ 生徒選択時 またはタブ切り替え時は実行

        # --- ここから戻り値を確実に返すための構造 ---
        table_content = None
        university_options = []
        subject_options = []

        if not student_id:
            table_content = dbc.Alert("まず生徒を選択してください。", color="info", className="mt-4")
            return table_content, university_options, subject_options

        try:
            results = get_past_exam_results_for_student(student_id)
            # 日付オブジェクトを 'YYYY-MM-DD' 文字列に変換（DataFrame作成前に）
            for r in results:
                r['date'] = r['date'].isoformat() if isinstance(r['date'], date) else None

            df = pd.DataFrame(results) if results else pd.DataFrame()

            if df.empty:
                table_content = dbc.Alert("この生徒の過去問結果はまだありません。", color="info", className="mt-4")
            else:
                # オプション生成
                university_options = [{'label': u, 'value': u} for u in sorted(df['university_name'].dropna().unique())]
                subject_options = [{'label': s, 'value': s} for s in sorted(df['subject'].dropna().unique())]

                # フィルター処理
                df_filtered = df.copy()
                if selected_university:
                    df_filtered = df_filtered[df_filtered['university_name'] == selected_university]
                if selected_subject:
                    df_filtered = df_filtered[df_filtered['subject'] == selected_subject]

                if df_filtered.empty:
                    table_content = dbc.Alert("フィルターに一致する過去問結果はありません。", color="warning", className="mt-4")
                else:
                    # テーブル生成ロジック (変更なし)
                    def calculate_percentage(row):
                        correct, total = row['correct_answers'], row['total_questions']
                        return f"{(correct / total * 100):.1f}%" if pd.notna(correct) and pd.notna(total) and total > 0 else ""
                    df_filtered['正答率'] = df_filtered.apply(calculate_percentage, axis=1)
                    def format_time(row):
                        req, total = row['time_required'], row['total_time_allowed']
                        # NaNでないことを確認してから整数変換
                        req_int = int(req) if pd.notna(req) else None
                        total_int = int(total) if pd.notna(total) else None
                        if req_int is not None and total_int is not None: return f"{req_int}/{total_int}"
                        return f"{req_int}" if req_int is not None else ""
                    df_filtered['所要時間(分)'] = df_filtered.apply(format_time, axis=1)

                    # 表示用に NaN を空文字列に置換
                    df_display = df_filtered.fillna('')

                    table_header = [html.Thead(html.Tr([html.Th("日付"), html.Th("大学名"), html.Th("学部名"), html.Th("入試方式"), html.Th("年度"), html.Th("科目"),
                                                        html.Th("所要時間(分)"), html.Th("正答率"), html.Th("操作", style={'width': '100px'})]))] # 幅調整
                    table_body = [html.Tbody([html.Tr([html.Td(row['date']), html.Td(row['university_name']), html.Td(row['faculty_name']),
                                                        html.Td(row['exam_system']), html.Td(row['year']), html.Td(row['subject']),
                                                        html.Td(row['所要時間(分)']), html.Td(row['正答率']),
                                                        html.Td([dbc.Button("編集", id={'type': 'edit-past-exam-btn', 'index': row['id']}, size="sm", className="me-1"),
                                                                 # テーブル内の削除ボタンはダイアログを開くだけにする
                                                                 dbc.Button("削除", id={'type': 'delete-past-exam-trigger-btn', 'index': row['id']}, color="danger", size="sm", outline=True)])
                                                      ]) for _, row in df_display.iterrows()])] # df_display を使用
                    table_content = dbc.Table(table_header + table_body, striped=True, bordered=True, hover=True, responsive=True, size="sm") # size="sm" 追加

        except Exception as e:
            print(f"Error in update_past_exam_table: {e}")
            table_content = dbc.Alert(f"テーブル表示中にエラーが発生しました: {e}", color="danger")

        return table_content, university_options, subject_options

    # ★★★ 修正箇所 (display_delete_past_exam_confirm_from_table) ★★★
    @app.callback(
        Output('delete-past-exam-confirm', 'displayed', allow_duplicate=True),
        Output('editing-past-exam-id-store', 'data', allow_duplicate=True), # 削除対象IDをセット
        Input({'type': 'delete-past-exam-trigger-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def display_delete_past_exam_confirm_from_table(delete_clicks):
        ctx = callback_context
        # ★ トリガーがない、またはトリガーの値がfalsy (None, 0) の場合は中断
        if not ctx.triggered or not ctx.triggered[0]['value']:
            raise PreventUpdate
        result_id = ctx.triggered_id['index']
        return True, result_id
    # ★★★ 修正ここまで ★★★


    # --- 大学合否タブ関連のコールバック ---
    # (handle_acceptance_modal_opening - 変更なし)
    @app.callback(
        [Output('acceptance-modal', 'is_open'),
         Output('acceptance-modal-title', 'children'),
         Output('editing-acceptance-id-store', 'data'), # 削除用にIDを保持
         Output('acceptance-university', 'value'), Output('acceptance-faculty', 'value'),
         Output('acceptance-department', 'value'), Output('acceptance-system', 'value'),
         Output('acceptance-result', 'value'), # ★ 合否結果を追加
         Output('acceptance-application-deadline', 'date'),
         Output('acceptance-exam-date', 'date'), Output('acceptance-announcement-date', 'date'),
         Output('acceptance-procedure-deadline', 'date'),
         Output('acceptance-modal-alert', 'is_open')],
        [Input('open-acceptance-modal-btn', 'n_clicks'), Input({'type': 'edit-acceptance-btn', 'index': ALL}, 'n_clicks'),
         Input('cancel-acceptance-modal-btn', 'n_clicks')],
        [State('student-selection-store', 'data')],
        prevent_initial_call=True
    )
    def handle_acceptance_modal_opening(add_clicks, edit_clicks_list, cancel_clicks, student_id):
        ctx = callback_context
        triggered_id_str = ctx.triggered_id if isinstance(ctx.triggered_id, str) else json.dumps(ctx.triggered_id)

        # どのボタンも押されていない、または edit ボタンで n_clicks が 0 の場合
        if not ctx.triggered or (isinstance(ctx.triggered_id, dict) and not ctx.triggered[0]['value']):
            raise PreventUpdate

        trigger_id = ctx.triggered_id

        # キャンセルボタン
        if trigger_id == 'cancel-acceptance-modal-btn':
            # ★ 出力変数が1つ増えたので no_update の数を調整
            return False, no_update, None, "", "", "", "", "", None, None, None, None, False

        # 新規追加ボタン
        if trigger_id == 'open-acceptance-modal-btn':
             # ★ 出力変数が1つ増えたので "" を追加
            return True, "大学合否結果の追加", None, "", "", "", "", "", None, None, None, None, False

        # 編集ボタン (パターンマッチング)
        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'edit-acceptance-btn':
            if not student_id: raise PreventUpdate # 生徒が選択されていない場合
            result_id = trigger_id['index']
            results = get_acceptance_results_for_student(student_id) # date オブジェクトを含むリスト
            result_to_edit = next((r for r in results if r['id'] == result_id), None)

            if result_to_edit:
                # 日付オブジェクトをYYYY-MM-DD文字列に変換 (Noneチェックも行う)
                def format_date(date_obj):
                    return date_obj.isoformat() if isinstance(date_obj, date) else None

                app_deadline = format_date(result_to_edit.get('application_deadline'))
                exam_date = format_date(result_to_edit.get('exam_date'))
                announcement_date = format_date(result_to_edit.get('announcement_date'))
                proc_deadline = format_date(result_to_edit.get('procedure_deadline'))
                result_value = result_to_edit.get('result', '') # Noneなら空文字

                # ★ result_value を追加して返す
                return (True, "大学合否結果の編集", result_id, result_to_edit.get('university_name', ''), result_to_edit.get('faculty_name', ''),
                        result_to_edit.get('department_name', ''), result_to_edit.get('exam_system', ''),
                        result_value, # ★ 合否結果
                        app_deadline, exam_date, announcement_date, proc_deadline, False)

        # 上記以外の場合はモーダルを閉じるか、状態を維持
        # ★ 出力変数が1つ増えたので no_update の数を調整
        return False, no_update, None, "", "", "", "", "", None, None, None, None, False

    # (save_acceptance_result - 変更なし)
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
         State('acceptance-result', 'value'), # ★ 合否結果 State を追加
         State('acceptance-application-deadline', 'date'),
         State('acceptance-exam-date', 'date'),
         State('acceptance-announcement-date', 'date'),
         State('acceptance-procedure-deadline', 'date')],
        prevent_initial_call=True
    )
    def save_acceptance_result(n_clicks, result_id, student_id, university, faculty, department, system,
                             result_val, app_deadline, exam_date, announcement_date, proc_deadline): # ★ result_val を追加
        if not n_clicks or not student_id: raise PreventUpdate
        if not university or not faculty: return dbc.Alert("大学名と学部名は必須です。", color="warning"), True, no_update, no_update, no_update

        # result_val が空文字列なら None に変換
        result_to_save = result_val if result_val else None

        result_data = {'university_name': university, 'faculty_name': faculty, 'department_name': department or None, 'exam_system': system or None,
                       'result': result_to_save, # ★ 保存するデータに追加
                       'application_deadline': app_deadline, 'exam_date': exam_date,
                       'announcement_date': announcement_date, 'procedure_deadline': proc_deadline}

        target_month_str = no_update
        date_candidates = [d for d in [app_deadline, exam_date, announcement_date, proc_deadline] if d]
        if date_candidates:
            try:
                earliest_date_obj = min([date.fromisoformat(d_str) for d_str in date_candidates])
                target_month_str = earliest_date_obj.strftime('%Y-%m')
            except (ValueError, TypeError): pass

        if result_id: success, message = update_acceptance_result(result_id, result_data)
        else: success, message = add_acceptance_result(student_id, result_data)

        if success:
            toast_message = message # 簡潔なメッセージに変更
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': toast_message, 'source': 'acceptance'}
            return "", False, toast_data, False, target_month_str
        else: return dbc.Alert(message, color="danger"), True, no_update, no_update, no_update

    # (update_acceptance_status_dropdown - 変更なし)
    @app.callback(
        Output('toast-trigger', 'data', allow_duplicate=True),
        Input({'type': 'acceptance-result-dropdown', 'index': ALL}, 'value'),
        State({'type': 'acceptance-result-dropdown', 'index': ALL}, 'id'),
        State('student-selection-store', 'data'),
        prevent_initial_call=True
    )
    def update_acceptance_status_dropdown(dropdown_values, dropdown_ids, student_id):
        ctx = callback_context
        # トリガーIDがリストでない場合（起動時など）は何もしない
        if not ctx.triggered_id or not isinstance(ctx.triggered_id, dict):
             raise PreventUpdate

        triggered_id_dict = ctx.triggered_id
        result_id = triggered_id_dict['index']

        # トリガーされたInputの値を取得 (Inputがリストなのでインデックスでアクセス)
        trigger_index = -1
        for i, d_id in enumerate(dropdown_ids):
             if d_id['index'] == result_id:
                 trigger_index = i
                 break
        if trigger_index == -1: raise PreventUpdate # 対象が見つからない場合

        new_result = dropdown_values[trigger_index]

        success, message = update_acceptance_result(result_id, {'result': new_result if new_result else None}) # 空文字列をNoneに
        if success:
            # メッセージを簡潔に
            message = "合否情報を更新しました。"
        else: message = f"合否情報の更新に失敗しました: {message}"
        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'acceptance'}
        return toast_data

    # ★★★ 修正箇所 (display_delete_acceptance_confirmation) ★★★
    @app.callback(
        [Output('delete-acceptance-confirm', 'displayed'),
         Output('editing-acceptance-id-store', 'data', allow_duplicate=True)],
        Input({'type': 'delete-acceptance-btn', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def display_delete_acceptance_confirmation(delete_clicks):
        ctx = callback_context
        # ★ トリガーがない、またはトリガーの値がfalsy (None, 0) の場合は中断
        if not ctx.triggered or not ctx.triggered[0]['value']:
            raise PreventUpdate
        result_id = ctx.triggered_id['index']
        return True, result_id
    # ★★★ 修正ここまで ★★★

    # (execute_acceptance_delete - 変更なし)
    @app.callback(
        [Output('toast-trigger', 'data', allow_duplicate=True),
         Output('editing-acceptance-id-store', 'data', allow_duplicate=True)], # IDをクリア
        Input('delete-acceptance-confirm', 'submit_n_clicks'),
        State('editing-acceptance-id-store', 'data'),
        prevent_initial_call=True
    )
    def execute_acceptance_delete(submit_n_clicks, result_id):
        if not submit_n_clicks or result_id is None:
            raise PreventUpdate
        success, message = delete_acceptance_result(result_id)
        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'acceptance'}
        # 成功したらIDストアをクリア
        return toast_data, None if success else no_update

    # (update_acceptance_table - 変更なし、前回の修正を維持)
    @app.callback(
        Output('acceptance-table-container', 'children'),
        [Input('student-selection-store', 'data'),
         Input('toast-trigger', 'data'),
         Input('refresh-acceptance-table-btn', 'n_clicks'),
         Input('past-exam-tabs', 'active_tab')], # ★ Input として active_tab
    )
    def update_acceptance_table(student_id, toast_data, refresh_clicks, active_tab):
        ctx = callback_context
        triggered_id = ctx.triggered_id if ctx.triggered_id else 'initial load'

        # ★ 入試管理タブが表示されていない場合は更新しない
        if active_tab != 'tab-acceptance':
            raise PreventUpdate

        # PreventUpdate 条件
        if triggered_id == 'toast-trigger':
            if not toast_data or toast_data.get('source') != 'acceptance':
                raise PreventUpdate
        elif triggered_id == 'refresh-acceptance-table-btn' and refresh_clicks is None:
             raise PreventUpdate
        # ★ 生徒選択時 またはタブ切り替え時は実行

        if not student_id:
            return dbc.Alert("まず生徒を選択してください。", color="info", className="mt-4")

        try:
            results = get_acceptance_results_for_student(student_id)
            if not results:
                return dbc.Alert("この生徒の入試予定・結果はまだありません。", color="info", className="mt-4")

            # DataFrameに変換（日付はオブジェクトのまま）
            df = pd.DataFrame(results)

            def create_result_dropdown(id_val, result_val):
                options = [ {'label': '未定', 'value': ''}, {'label': '合格', 'value': '合格'}, {'label': '不合格', 'value': '不合格'}, {'label': '補欠', 'value': '補欠'}, ]
                value_to_set = result_val if result_val else ''
                return dcc.Dropdown( id={'type': 'acceptance-result-dropdown', 'index': id_val}, options=options, value=value_to_set, placeholder="結果を選択...", clearable=False, style={'minWidth': '100px'} )

            table_header = [ html.Thead(html.Tr([ html.Th("大学名"), html.Th("学部"), html.Th("学科"), html.Th("方式"), html.Th("出願"), html.Th("受験日"), html.Th("発表日"), html.Th("手続"), html.Th("合否", style={'width': '120px'}), html.Th("操作", style={'width': '100px'}), ])) ] # 幅調整

            table_body_rows = []
            for _, row in df.iterrows():
                # 日付オブジェクトを YYYY-MM-DD 文字列に変換、Noneなら'-'
                def format_date_td(date_obj):
                    return date_obj.strftime('%Y-%m-%d') if isinstance(date_obj, date) else '-'

                table_body_rows.append(html.Tr([
                    html.Td(row.get('university_name', '')),
                    html.Td(row.get('faculty_name', '')),
                    html.Td(row.get('department_name', '') or '-'),
                    html.Td(row.get('exam_system', '') or '-'),
                    html.Td(format_date_td(row.get('application_deadline'))),
                    html.Td(format_date_td(row.get('exam_date'))),
                    html.Td(format_date_td(row.get('announcement_date'))),
                    html.Td(format_date_td(row.get('procedure_deadline'))),
                    html.Td(create_result_dropdown(row['id'], row.get('result'))),
                    html.Td([
                        dbc.Button("編集", id={'type': 'edit-acceptance-btn', 'index': row['id']}, size="sm", className="me-1"),
                        dbc.Button("削除", id={'type': 'delete-acceptance-btn', 'index': row['id']}, color="danger", size="sm", outline=True)
                    ])
                ]))
            table_body = [html.Tbody(table_body_rows)]
            return dbc.Table(table_header + table_body, striped=True, bordered=True, hover=True, responsive=True, size="sm") # size="sm"追加

        except Exception as e:
            print(f"Error in update_acceptance_table: {e}")
            return dbc.Alert(f"テーブル表示中にエラーが発生しました: {e}", color="danger")


    # --- カレンダータブ関連のコールバック ---
    # (update_acceptance_calendar - 変更なし、前回の修正を維持)
    @app.callback(
        Output('web-calendar-container', 'children'),
        [Input('student-selection-store', 'data'),
         Input('toast-trigger', 'data'),
         Input('current-calendar-month-store', 'data'),
         Input('refresh-calendar-btn', 'n_clicks'),
         Input('past-exam-tabs', 'active_tab')], # ★ Input として active_tab
    )
    def update_acceptance_calendar(student_id, toast_data, target_month, refresh_clicks, active_tab):
        ctx = callback_context
        triggered_id = ctx.triggered_id if ctx.triggered_id else 'initial load'

        # ★ カレンダータブが表示されていない場合は更新しない
        if active_tab != 'tab-gantt':
            raise PreventUpdate

        if triggered_id == 'toast-trigger':
            if not toast_data or toast_data.get('source') != 'acceptance':
                raise PreventUpdate
        elif triggered_id == 'refresh-calendar-btn' and refresh_clicks is None:
             raise PreventUpdate

        if not target_month:
             if student_id:
                 acceptance_data_for_init = get_acceptance_results_for_student(student_id)
                 target_month = find_nearest_future_month(acceptance_data_for_init)
             else:
                 target_month = date.today().strftime('%Y-%m')

        if not student_id:
            # ★ 空データでカレンダー生成 (エラーにしない)
            return create_html_calendar([], target_month)

        try:
             acceptance_data = get_acceptance_results_for_student(student_id) # dateオブジェクトを含む
             calendar_html = create_html_calendar(acceptance_data, target_month) # dateオブジェクトを渡す
             return calendar_html
        except Exception as e:
            print(f"Error in update_acceptance_calendar: {e}")
            return dbc.Alert(f"カレンダー表示中にエラーが発生しました: {e}", color="danger")

    # (update_calendar_month - 変更なし)
    @app.callback(
        Output('current-calendar-month-store', 'data'),
        [Input('prev-month-btn', 'n_clicks'),
         Input('next-month-btn', 'n_clicks'),
         Input('past-exam-tabs', 'active_tab'),
         Input('student-selection-store', 'data')],
        [State('current-calendar-month-store', 'data')],
        prevent_initial_call=True
    )
    def update_calendar_month(prev_clicks, next_clicks, active_tab, student_id, current_month_str):
        ctx = callback_context
        trigger_id = ctx.triggered_id

        # カレンダータブ以外なら更新しない
        if active_tab != 'tab-gantt':
             raise PreventUpdate
        
        # ★ タブ切り替え時 or 生徒変更時 (active_tab != 'tab-gantt' のチェックより後に移動)
        if trigger_id in ['past-exam-tabs', 'student-selection-store']:
            if not student_id: return date.today().strftime('%Y-%m') # 生徒未選択なら当月
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
            new_month = current_month.replace(day=1) - relativedelta(months=1) # relativedeltaを使用
            return new_month.strftime('%Y-%m')
        elif trigger_id == 'next-month-btn':
            new_month = current_month.replace(day=1) + relativedelta(months=1) # relativedeltaを使用
            return new_month.strftime('%Y-%m')

        raise PreventUpdate

    # (display_current_month - 変更なし)
    @app.callback(
        Output('current-month-display', 'children'),
        Input('current-calendar-month-store', 'data')
    )
    def display_current_month(month_str):
        if not month_str: month_str = date.today().strftime('%Y-%m')
        try: dt = datetime.strptime(month_str, '%Y-%m'); return f"{dt.year}年 {dt.month}月"
        except (ValueError, TypeError): today = date.today(); return f"{today.year}年 {today.month}月"

    # (update_printable_calendar - 変更なし)
    @app.callback(
        Output('printable-calendar-area', 'children'),
        [Input('student-selection-store', 'data'),
         Input('toast-trigger', 'data')],
        prevent_initial_call=True
    )
    def update_printable_calendar(student_id, toast_data):
        ctx = callback_context
        triggered_id = ctx.triggered_id if ctx.triggered_id else 'initial load'

        if triggered_id == 'toast-trigger':
            if not toast_data or toast_data.get('source') != 'acceptance': raise PreventUpdate
        elif not student_id: return []

        acceptance_data = get_acceptance_results_for_student(student_id)
        if not acceptance_data: return [dbc.Alert("印刷対象の受験・合否データがありません。", color="info")]

        df = pd.DataFrame(acceptance_data)
        all_dates = []
        date_cols = ['application_deadline', 'exam_date', 'announcement_date', 'procedure_deadline']
        # dateオブジェクトのリストを作成
        for col in date_cols:
             if col in df.columns:
                 # Noneでないdateオブジェクトのみを追加
                 valid_dates = [d for d in df[col] if isinstance(d, date)]
                 all_dates.extend(valid_dates)

        if not all_dates: return [dbc.Alert("有効な日付データがありません。", color="warning")]

        min_date_obj = min(all_dates).replace(day=1)
        max_date_obj = max(all_dates).replace(day=1)

        printable_tables = []
        current_month_loop = min_date_obj

        # DataFrameの日付列をdatetimeに変換 (create_single_month_tableで使うため)
        dt_cols_print = ['app_deadline_dt', 'exam_dt', 'announcement_dt', 'proc_deadline_dt']
        for col, dt_col in zip(date_cols, dt_cols_print):
            if col in df.columns:
                 # dateオブジェクトをdatetimeに変換
                 df[dt_col] = df[col].apply(lambda x: datetime.combine(x, datetime.min.time()) if isinstance(x, date) else pd.NaT)
            else: df[dt_col] = pd.NaT

        sort_keys_print = []
        if 'app_deadline_dt' in df.columns: sort_keys_print.append('app_deadline_dt')
        if 'exam_dt' in df.columns: sort_keys_print.append('exam_dt')
        sort_keys_print.extend(['university_name', 'faculty_name'])
        df_all_sorted_print = df.sort_values(by=sort_keys_print, ascending=True, na_position='last') if sort_keys_print and not df.empty else df

        while current_month_loop <= max_date_obj:
            year, month = current_month_loop.year, current_month_loop.month
            printable_tables.append(create_single_month_table(df_all_sorted_print, year, month))
            current_month_loop += relativedelta(months=+1)

        return printable_tables

    # (印刷用clientside_callback - 変更なし)
    clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks > 0) {
                const style = document.createElement('style');
                style.innerHTML = `
                    @media print {
                        .printable-only { display: block !important; }
                        .printable-hide { display: none !important; }
                        body, #page-content { background-color: white !important; }
                        #printable-calendar-area .single-month-wrapper { page-break-inside: avoid !important; margin-bottom: 15px !important; } /* wrapperにスタイル適用 */
                        #printable-calendar-area .calendar-month-header { page-break-before: auto; page-break-after: avoid; font-size: 11pt !important; font-weight: bold; text-align: center; margin-bottom: 5px !important;} /* 月ヘッダースタイル */
                        #printable-calendar-area .calendar-table { width: 100% !important; font-size: 7pt !important; border: 1px solid #ccc !important; table-layout: fixed !important; page-break-inside: avoid !important; margin-bottom: 0 !important; border-collapse: collapse !important; }
                        #printable-calendar-area .calendar-table th, #printable-calendar-area .calendar-table td { border: 1px solid #ccc !important; padding: 2px !important; white-space: normal !important; word-wrap: break-word; vertical-align: middle !important; height: 22px !important; text-align: center !important; overflow: hidden; text-overflow: ellipsis; box-sizing: border-box; }
                        #printable-calendar-area .calendar-info-header-cell, #printable-calendar-area .calendar-info-cell { width: 80px !important; font-size: 6pt !important; vertical-align: top !important; white-space: normal !important; height: auto !important; position: static !important; left: auto !important; z-index: auto !important; background-color: #f8f9fa !important; }
                        #printable-calendar-area .calendar-info-header-cell { vertical-align: middle !important; font-weight: bold; background-color: #e9ecef !important;}
                        #printable-calendar-area .calendar-header-cell, #printable-calendar-area .calendar-date-cell { width: auto !important; min-width: 0 !important; font-size: 7pt !important; }
                        #printable-calendar-area .calendar-header-cell { font-size: 6pt !important; }
                         #printable-calendar-area .calendar-table th br { display: block !important; }
                        #printable-calendar-area .saturday { background-color: #f0f8ff !important; }
                        #printable-calendar-area .sunday { background-color: #fff7f0 !important; }
                        #printable-calendar-area .app-deadline-cell { background-color: #ffff7f !important; }
                        #printable-calendar-area .exam-date-cell { background-color: #ff7f7f !important; }
                        #printable-calendar-area .announcement-date-cell { background-color: #7fff7f !important; }
                        #printable-calendar-area .proc-deadline-cell { background-color: #bf7fff !important; }
                        #printable-calendar-area .app-deadline-cell, #printable-calendar-area .exam-date-cell, #printable-calendar-area .announcement-date-cell, #printable-calendar-area .proc-deadline-cell, #printable-calendar-area .saturday, #printable-calendar-area .sunday { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
                        @page { size: A4 portrait; margin: 10mm; }
                    }
                `;
                document.head.appendChild(style);
                setTimeout(function() {
                    window.print();
                    setTimeout(() => { document.head.removeChild(style); }, 500);
                }, 500);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('print-calendar-btn', 'n_clicks', allow_duplicate=True),
        Input('print-calendar-btn', 'n_clicks'),
        prevent_initial_call=True
    )


    # (handle_mock_exam_modal_opening - 変更なし)
    @app.callback(
        [Output('mock-exam-modal', 'is_open'),
         Output('mock-exam-modal-title', 'children'),
         Output('editing-mock-exam-id-store', 'data'), # 編集/削除用IDストア
         # --- モーダル内の各入力フィールド ---
         Output('mock-exam-result-type', 'value'), Output('mock-exam-name', 'value'),
         Output('mock-exam-format', 'value'), Output('mock-exam-grade', 'value'), Output('mock-exam-round', 'value'),
         Output('mock-exam-date', 'date'),
         # 記述
         Output('mock-exam-kokugo-desc', 'value'), Output('mock-exam-math-desc', 'value'), Output('mock-exam-english-desc', 'value'),
         Output('mock-exam-rika1-desc', 'value'), Output('mock-exam-rika2-desc', 'value'), Output('mock-exam-shakai1-desc', 'value'), Output('mock-exam-shakai2-desc', 'value'),
         # マーク
         Output('mock-exam-kokugo-mark', 'value'), Output('mock-exam-math1a-mark', 'value'), Output('mock-exam-math2bc-mark', 'value'),
         Output('mock-exam-english-r-mark', 'value'), Output('mock-exam-english-l-mark', 'value'), Output('mock-exam-rika1-mark', 'value'), Output('mock-exam-rika2-mark', 'value'),
         Output('mock-exam-shakai1-mark', 'value'), Output('mock-exam-shakai2-mark', 'value'), Output('mock-exam-rika-kiso1-mark', 'value'),
         Output('mock-exam-rika-kiso2-mark', 'value'), Output('mock-exam-info-mark', 'value'),
         # アラート
         Output('mock-exam-modal-alert', 'is_open')],
        [Input('open-mock-exam-modal-btn', 'n_clicks'),
         Input({'type': 'edit-mock-exam-btn', 'index': ALL}, 'n_clicks'),
         Input('cancel-mock-exam-modal-btn', 'n_clicks')],
        [State('student-selection-store', 'data')],
        prevent_initial_call=True
    )
    def handle_mock_exam_modal_opening(add_clicks, edit_clicks_list, cancel_clicks, student_id):
        ctx = callback_context
        # どのボタンも押されていない、または edit ボタンで n_clicks が 0 の場合
        if not ctx.triggered or (isinstance(ctx.triggered_id, dict) and not ctx.triggered[0]['value']):
            raise PreventUpdate

        trigger_id = ctx.triggered_id

        # デフォルト値（空）のリストを作成 (出力数: 3 + 6 + 7 + 12 + 1 = 29)
        num_fields_total = 29
        initial_values = [None] * (num_fields_total - 3 - 1) # is_open, title, store, alertを除く
        initial_values = [ # より具体的に初期化
            None, # result_type
            None, # name
            None, # format
            None, # grade
            None, # round
            None, # date
        ] + [None] * 19 # Scores (7 記述 + 12 マーク)

        # キャンセルボタン
        if trigger_id == 'cancel-mock-exam-modal-btn':
            return [False, no_update, None] + initial_values + [False]

        # 新規追加ボタン
        if trigger_id == 'open-mock-exam-modal-btn':
            today_iso = date.today().isoformat() # 今日の日付を文字列で
            return [True, "模試結果の入力", None] + [None]*5 + [today_iso] + [None]*19 + [False] # 日付だけ今日に


        # 編集ボタン (パターンマッチング)
        if isinstance(trigger_id, dict) and trigger_id.get('type') == 'edit-mock-exam-btn':
            if not student_id: raise PreventUpdate # 生徒が選択されていない場合
            result_id = trigger_id['index']
            results = get_mock_exam_results_for_student(student_id)
            result_to_edit = next((r for r in results if r['id'] == result_id), None)

            if result_to_edit:
                # 辞書から値を取得、存在しない場合はNone
                values = [
                    result_to_edit.get('result_type'),
                    result_to_edit.get('mock_exam_name'),
                    result_to_edit.get('mock_exam_format'),
                    result_to_edit.get('grade'),
                    result_to_edit.get('round'),
                    # 日付オブジェクトをYYYY-MM-DD文字列に変換
                    result_to_edit.get('exam_date').isoformat() if isinstance(result_to_edit.get('exam_date'), date) else None,
                    # 点数 (Noneの可能性あり)
                    result_to_edit.get('subject_kokugo_desc'), result_to_edit.get('subject_math_desc'), result_to_edit.get('subject_english_desc'),
                    result_to_edit.get('subject_rika1_desc'), result_to_edit.get('subject_rika2_desc'), result_to_edit.get('subject_shakai1_desc'), result_to_edit.get('subject_shakai2_desc'),
                    result_to_edit.get('subject_kokugo_mark'), result_to_edit.get('subject_math1a_mark'), result_to_edit.get('subject_math2bc_mark'),
                    result_to_edit.get('subject_english_r_mark'), result_to_edit.get('subject_english_l_mark'), result_to_edit.get('subject_rika1_mark'), result_to_edit.get('subject_rika2_mark'),
                    result_to_edit.get('subject_shakai1_mark'), result_to_edit.get('subject_shakai2_mark'), result_to_edit.get('subject_rika_kiso1_mark'),
                    result_to_edit.get('subject_rika_kiso2_mark'), result_to_edit.get('subject_info_mark')
                ]
                # Noneの代わりに空文字列を使うべきか？ -> Noneのままの方が扱いやすい
                return [True, "模試結果の編集", result_id] + values + [False]

        # 上記以外の場合はモーダルを閉じる
        return [False, no_update, None] + initial_values + [False]

    # (save_mock_exam_result - 変更なし)
    @app.callback(
        [Output('mock-exam-modal-alert', 'children'),
         Output('mock-exam-modal-alert', 'is_open', allow_duplicate=True),
         Output('toast-trigger', 'data', allow_duplicate=True),
         Output('mock-exam-modal', 'is_open', allow_duplicate=True)],
        Input('save-mock-exam-modal-btn', 'n_clicks'),
        [State('editing-mock-exam-id-store', 'data'),
         State('student-selection-store', 'data'),
         # --- モーダル内の各入力フィールド ---
         State('mock-exam-result-type', 'value'), State('mock-exam-name', 'value'),
         State('mock-exam-format', 'value'), State('mock-exam-grade', 'value'), State('mock-exam-round', 'value'),
         State('mock-exam-date', 'date'),
         # 記述
         State('mock-exam-kokugo-desc', 'value'), State('mock-exam-math-desc', 'value'), State('mock-exam-english-desc', 'value'),
         State('mock-exam-rika1-desc', 'value'), State('mock-exam-rika2-desc', 'value'), State('mock-exam-shakai1-desc', 'value'), State('mock-exam-shakai2-desc', 'value'),
         # マーク
         State('mock-exam-kokugo-mark', 'value'), State('mock-exam-math1a-mark', 'value'), State('mock-exam-math2bc-mark', 'value'),
         State('mock-exam-english-r-mark', 'value'), State('mock-exam-english-l-mark', 'value'), State('mock-exam-rika1-mark', 'value'), State('mock-exam-rika2-mark', 'value'),
         State('mock-exam-shakai1-mark', 'value'), State('mock-exam-shakai2-mark', 'value'), State('mock-exam-rika-kiso1-mark', 'value'),
         State('mock-exam-rika-kiso2-mark', 'value'), State('mock-exam-info-mark', 'value')],
        prevent_initial_call=True
    )
    def save_mock_exam_result(n_clicks, result_id, student_id,
                              res_type, name, format_val, grade, round_val, date_val, # 基本情報
                              ko_d, ma_d, en_d, r1_d, r2_d, s1_d, s2_d, # 記述
                              ko_m, m1a_m, m2b_m, enr_m, enl_m, r1_m, r2_m, s1_m, s2_m, rk1_m, rk2_m, inf_m # マーク
                              ):
        if not n_clicks or not student_id: raise PreventUpdate

        # 必須項目チェック
        required_data = {
            'result_type': res_type, 'mock_exam_name': name, 'mock_exam_format': format_val,
            'grade': grade, 'round': round_val
        }
        missing_fields = [k for k, v in required_data.items() if not v]
        if missing_fields:
             field_names_jp = {'result_type': '種類', 'mock_exam_name': '模試名', 'mock_exam_format': '形式', 'grade': '学年', 'round': '回数'}
             missing_jp = [field_names_jp.get(f, f) for f in missing_fields]
             return dbc.Alert(f"{'、'.join(missing_jp)} は必須です。", color="warning"), True, no_update, no_update

        # データ辞書作成
        data_to_save = {
            'result_type': res_type, 'mock_exam_name': name, 'mock_exam_format': format_val,
            'grade': grade, 'round': round_val, 'exam_date': date_val,
            'subject_kokugo_desc': ko_d, 'subject_math_desc': ma_d, 'subject_english_desc': en_d,
            'subject_rika1_desc': r1_d, 'subject_rika2_desc': r2_d, 'subject_shakai1_desc': s1_d, 'subject_shakai2_desc': s2_d,
            'subject_kokugo_mark': ko_m, 'subject_math1a_mark': m1a_m, 'subject_math2bc_mark': m2b_m,
            'subject_english_r_mark': enr_m, 'subject_english_l_mark': enl_m, 'subject_rika1_mark': r1_m, 'subject_rika2_mark': r2_m,
            'subject_shakai1_mark': s1_m, 'subject_shakai2_mark': s2_m, 'subject_rika_kiso1_mark': rk1_m,
            'subject_rika_kiso2_mark': rk2_m, 'subject_info_mark': inf_m
        }
        # 空文字列やNoneでない数値以外をNoneに変換 (add/update関数側でも処理する)
        for key, value in data_to_save.items():
            if key.startswith('subject_'):
                try:
                    # Allow 0 but treat empty string or non-numeric as None
                    if value is None or str(value).strip() == '':
                        data_to_save[key] = None
                    else:
                        data_to_save[key] = int(value)
                except (ValueError, TypeError):
                    data_to_save[key] = None
            elif value == '': # 他のフィールドで空文字列はNoneに
                 data_to_save[key] = None


        if result_id: success, message = update_mock_exam_result(result_id, data_to_save)
        else: success, message = add_mock_exam_result(student_id, data_to_save)

        if success:
            toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'mock_exam'}
            return "", False, toast_data, False
        else: return dbc.Alert(message, color="danger"), True, no_update, no_update

    # ★★★ 修正箇所 (display_delete_mock_exam_confirmation) ★★★
    @app.callback(
        [Output('delete-mock-exam-confirm', 'displayed'),
         Output('editing-mock-exam-id-store', 'data', allow_duplicate=True)], # IDをストアに出力
        [Input({'type': 'delete-mock-exam-trigger-btn', 'index': ALL}, 'n_clicks'), # テーブル内のボタン
         Input('delete-mock-exam-btn', 'n_clicks')], # モーダル内のボタン
        [State('editing-mock-exam-id-store', 'data')], # モーダル用ID (モーダルボタン用)
        prevent_initial_call=True
    )
    def display_delete_mock_exam_confirmation(table_clicks, modal_click, result_id_from_modal):
        ctx = callback_context
        if not ctx.triggered: 
            raise PreventUpdate

        triggered_id = ctx.triggered_id
        triggered_value = ctx.triggered[0]['value'] # ★ トリガーされた値を取得

        result_id_to_delete = None

        if isinstance(triggered_id, dict) and triggered_id.get('type') == 'delete-mock-exam-trigger-btn':
            # テーブルのボタンが押された場合
            if not triggered_value or triggered_value == 0: # ★ トリガーされた値が None or 0 なら何もしない
                raise PreventUpdate
            result_id_to_delete = triggered_id['index'] # ★ テーブルボタンからIDを取得
        
        elif triggered_id == 'delete-mock-exam-btn':
            # モーダルの削除ボタンが押された場合
            if not modal_click or result_id_from_modal is None: 
                raise PreventUpdate
            result_id_to_delete = result_id_from_modal # StoreからIDを取得
        
        else:
             # ここに来ることはないはずだが、念のため
             raise PreventUpdate

        # IDが取得できたらダイアログ表示し、IDをストアに保存
        if result_id_to_delete is not None:
             return True, result_id_to_delete
             
        return False, no_update # ダイアログ非表示、ストアは更新しない
    # ★★★ 修正ここまで ★★★


    # (execute_mock_exam_delete - 変更なし)
    @app.callback(
        [Output('toast-trigger', 'data', allow_duplicate=True),
         Output('mock-exam-modal', 'is_open', allow_duplicate=True), # モーダルも閉じる
         Output('editing-mock-exam-id-store', 'data', allow_duplicate=True)], # IDクリア
        Input('delete-mock-exam-confirm', 'submit_n_clicks'),
        State('editing-mock-exam-id-store', 'data'), # 削除対象ID
        prevent_initial_call=True
    )
    def execute_mock_exam_delete(submit_n_clicks, result_id):
        if not submit_n_clicks or result_id is None:
            raise PreventUpdate
        success, message = delete_mock_exam_result(result_id)
        toast_data = {'timestamp': datetime.now().isoformat(), 'message': message, 'source': 'mock_exam'}
        # 成功したらモーダルを閉じ、IDストアをクリア
        return toast_data, not success, None if success else no_update

    # (update_mock_exam_tables - 変更なし、前回の修正を維持)
    @app.callback(
        [Output('mock-exam-mark-table-container', 'children'),
         Output('mock-exam-descriptive-table-container', 'children')],
        [Input('student-selection-store', 'data'),
         Input('toast-trigger', 'data'),
         Input('refresh-mock-exam-table-btn', 'n_clicks'),
         Input('past-exam-tabs', 'active_tab')], # ★ Input として active_tab
    )
    def update_mock_exam_tables(student_id, toast_data, refresh_clicks, active_tab):
        ctx = callback_context
        triggered_id = ctx.triggered_id if ctx.triggered_id else 'initial load'

        # ★ 模試結果タブが表示されていない場合は更新しない
        if active_tab != 'tab-mock-exam':
            raise PreventUpdate

        # PreventUpdate 条件
        if triggered_id == 'toast-trigger':
            if not toast_data or toast_data.get('source') != 'mock_exam':
                raise PreventUpdate
        elif triggered_id == 'refresh-mock-exam-table-btn' and refresh_clicks is None:
             raise PreventUpdate
        # ★ 生徒選択時 またはタブ切り替え時は実行

        if not student_id:
            no_student_alert = dbc.Alert("まず生徒を選択してください。", color="info", className="mt-4")
            return no_student_alert, no_student_alert # 両方のテーブルに表示

        try:
            results = get_mock_exam_results_for_student(student_id)
            if not results:
                 no_data_alert = dbc.Alert("この生徒の模試結果はまだありません。", color="info", className="mt-4")
                 return no_data_alert, no_data_alert

            df_all = pd.DataFrame(results)

            # マークと記述に分割
            df_mark = df_all[df_all['mock_exam_format'] == 'マーク'].copy()
            df_desc = df_all[df_all['mock_exam_format'] == '記述'].copy()

            # テーブル生成
            mark_table = _create_mock_exam_table(df_mark, "mark", student_id)
            desc_table = _create_mock_exam_table(df_desc, "descriptive", student_id)

            return mark_table, desc_table

        except Exception as e:
            print(f"Error in update_mock_exam_tables: {e}")
            error_alert = dbc.Alert(f"テーブル表示中にエラーが発生しました: {e}", color="danger")
            return error_alert, error_alert

    # ★★★ ここまで模試結果関連 ★★★