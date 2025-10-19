# charts/calendar_generator.py
import pandas as pd
from dash import html
from datetime import datetime, date, timedelta
import calendar
import dash_bootstrap_components as dbc
from dateutil.relativedelta import relativedelta

def create_html_calendar(acceptance_data, start_year_month, end_year_month):
    try:
        start_date = datetime.strptime(start_year_month, '%Y-%m').date().replace(day=1)
        # 終了日は end_year_month の最終日を計算
        end_month_start = datetime.strptime(end_year_month, '%Y-%m').date().replace(day=1)
        end_date = (end_month_start + relativedelta(months=+1)) - timedelta(days=1)
    except (ValueError, TypeError):
        today = date.today()
        start_date = today.replace(day=1, month=12) # 当年12月開始
        end_date = (start_date + relativedelta(months=+4)) - timedelta(days=1) # 翌年3月末まで

    # --- データ準備 (変更なし) ---
    df = pd.DataFrame([
        {'id': r.get('id'), 'university_name': r.get('university_name'),
         'faculty_name': r.get('faculty_name'), 'department_name': r.get('department_name'),
         'exam_system': r.get('exam_system'), 'result': r.get('result'),
         'application_deadline': r.get('application_deadline'), 'exam_date': r.get('exam_date'),
         'announcement_date': r.get('announcement_date'), 'procedure_deadline': r.get('procedure_deadline')}
        for r in acceptance_data
    ])
    if df.empty:
        return html.Div(dbc.Alert("表示する受験・合否データがありません。", color="info"))

    date_cols = ['application_deadline', 'exam_date', 'announcement_date', 'procedure_deadline']
    dt_cols = ['app_deadline_dt', 'exam_dt', 'announcement_dt', 'proc_deadline_dt']
    for col, dt_col in zip(date_cols, dt_cols):
        if col in df.columns: df[dt_col] = pd.to_datetime(df[col], errors='coerce')
        else: df[dt_col] = pd.NaT

    sort_keys = [col for col in ['app_deadline_dt', 'exam_dt'] if col in df.columns]
    df_all_sorted = df.sort_values(by=sort_keys, ascending=True, na_position='last') if sort_keys else df

    # --- 単一テーブルのヘッダー生成 ---
    header_cells = [html.Th("大学・学部等", className="calendar-info-header-cell", rowSpan=2)]
    month_cells = []
    day_cells = []
    current_date_header = start_date
    month_colspan = 0
    current_header_month = None
    weekday_names_jp = ["月", "火", "水", "木", "金", "土", "日"]

    while current_date_header <= end_date:
        year, month, day = current_date_header.year, current_date_header.month, current_date_header.day

        # 月ヘッダー
        if current_header_month != month:
            if current_header_month is not None:
                month_cells.append(html.Th(f"{last_year if current_header_month==12 else ''}{current_header_month}月", colSpan=month_colspan, className="calendar-month-header-cell"))
            current_header_month = month
            month_colspan = 0
            last_year = year # 年が変わる場合のために保持
        month_colspan += 1

        # 日ヘッダー
        weekday_index = current_date_header.weekday()
        weekday_name = weekday_names_jp[weekday_index]
        cell_class = "calendar-header-cell"
        if weekday_index == 5: cell_class += " saturday"
        elif weekday_index == 6: cell_class += " sunday"
        # 曜日を表示しないように変更
        day_cells.append(html.Th(str(day), className=cell_class, title=f"{year}-{month:02d}-{day:02d} ({weekday_name})"))

        current_date_header += timedelta(days=1)

    # 最後の月
    month_cells.append(html.Th(f"{last_year if current_header_month==12 else ''}{current_header_month}月", colSpan=month_colspan, className="calendar-month-header-cell"))

    header_row1 = html.Tr(header_cells + month_cells)
    header_row2 = html.Tr(day_cells)
    table_header = html.Thead([header_row1, header_row2])

    # --- テーブルボディ生成 ---
    body_rows = []
    for _, row in df_all_sorted.iterrows():
        # 情報セル (学科名・方式を戻す)
        info_parts = [
            html.Strong(f"{row.get('university_name','')} {row.get('faculty_name','') }"), html.Br(),
            row.get('department_name', ''), html.Br() if row.get('department_name') else '',
            html.Small(row.get('exam_system', ''), className="text-muted"),
        ]
        info_cell = html.Td(info_parts, className="calendar-info-cell")

        # 日付セル (期間全体をループ - 変更なし)
        date_cells = []
        current_date_loop = start_date
        while current_date_loop <= end_date:
            current_date_dt = current_date_loop # dateオブジェクトとして保持

            app_day = pd.notna(row.get('app_deadline_dt')) and row['app_deadline_dt'].date() == current_date_dt
            exam_day = pd.notna(row.get('exam_dt')) and row['exam_dt'].date() == current_date_dt
            announcement_day = pd.notna(row.get('announcement_dt')) and row['announcement_dt'].date() == current_date_dt
            proc_day = pd.notna(row.get('proc_deadline_dt')) and row['proc_deadline_dt'].date() == current_date_dt

            cell_classes = ["calendar-date-cell"]
            content = []
            title_texts = []
            weekday_index = current_date_loop.weekday()
            if weekday_index == 5: cell_classes.append("saturday")
            elif weekday_index == 6: cell_classes.append("sunday")

            is_proc = proc_day
            is_announce = announcement_day
            is_exam = exam_day
            is_app = app_day

            if is_proc: cell_classes.append("proc-deadline-cell"); content.append("手"); title_texts.append("手続期日")
            if is_announce: cell_classes.append("announcement-date-cell"); content.append("合"); title_texts.append("発表日")
            if is_exam: cell_classes.append("exam-date-cell"); content.append("受") if "手" not in content and "合" not in content else None; title_texts.append("受験日")
            if is_app: cell_classes.append("app-deadline-cell"); content.append("出") if not content else None; title_texts.append("出願期日")

            final_content = "/".join(content) if content else ""
            final_title = ", ".join(title_texts) if title_texts else ""
            date_cells.append(html.Td(final_content, className=" ".join(cell_classes), title=final_title))

            current_date_loop += timedelta(days=1)

        body_rows.append(html.Tr([info_cell] + date_cells))

    # --- テーブル全体を返す ---
    # ★ table タグに id を追加
    calendar_table = html.Table(
        id="full-calendar-table", # ★ ID追加
        className="calendar-table",
        children=[table_header, html.Tbody(body_rows)]
    )
    # ★ ラッパーDivを再度追加
    return html.Div(calendar_table, className="multi-month-calendar-wrapper") # ラッパークラス名変更