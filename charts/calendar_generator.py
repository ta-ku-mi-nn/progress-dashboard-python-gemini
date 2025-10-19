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
        end_date = (datetime.strptime(end_year_month, '%Y-%m').date().replace(day=1) + relativedelta(months=+1)) - timedelta(days=1)
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
    header_cells = [html.Th("大学・学部等", className="calendar-info-header-cell", rowSpan=2)] # 2行分結合
    month_cells = []
    day_cells = []
    current_date = start_date
    month_colspan = 0
    current_header_month = None
    weekday_names_jp = ["月", "火", "水", "木", "金", "土", "日"]

    while current_date <= end_date:
        year, month, day = current_date.year, current_date.month, current_date.day

        # 月ヘッダーの処理
        if current_header_month != month:
            if current_header_month is not None: # 前の月のcolspanを確定
                month_cells.append(html.Th(f"{year if month==1 else ''}{current_header_month}月", colSpan=month_colspan, className="calendar-month-header-cell"))
            current_header_month = month
            month_colspan = 0
        month_colspan += 1

        # 日ヘッダーの処理
        weekday_index = current_date.weekday()
        weekday_name = weekday_names_jp[weekday_index]
        cell_class = "calendar-header-cell"
        if weekday_index == 5: cell_class += " saturday"
        elif weekday_index == 6: cell_class += " sunday"
        day_cells.append(html.Th([str(day), html.Br(), weekday_name], className=cell_class, title=f"{year}-{month:02d}-{day:02d} ({weekday_name})"))

        current_date += timedelta(days=1)

    # 最後の月のcolspanを追加
    month_cells.append(html.Th(f"{end_date.year if end_date.month==1 else ''}{current_header_month}月", colSpan=month_colspan, className="calendar-month-header-cell"))

    header_row1 = html.Tr(header_cells + month_cells)
    header_row2 = html.Tr(day_cells)
    table_header = html.Thead([header_row1, header_row2])

    # --- テーブルボディ生成 ---
    body_rows = []
    for _, row in df_all_sorted.iterrows():
        # 情報セル (変更なし)
        info_parts = [
            html.Strong(f"{row.get('university_name','')} {row.get('faculty_name','') }"), html.Br(),
            row.get('department_name', ''), html.Br() if row.get('department_name') else '',
            html.Small(row.get('exam_system', ''), className="text-muted"),
        ]
        info_cell = html.Td(info_parts, className="calendar-info-cell")

        # 日付セル (期間全体をループ)
        date_cells = []
        current_date_loop = start_date
        while current_date_loop <= end_date:
            year, month, day = current_date_loop.year, current_date_loop.month, current_date_loop.day
            current_date_dt = current_date_loop # dateオブジェクトとして保持

            # 各日付がイベント日に該当するかチェック
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
    calendar_table = html.Table(
        className="calendar-table",
        children=[table_header, html.Tbody(body_rows)]
    )
    # ラッパーDivは不要になったので削除
    return calendar_table