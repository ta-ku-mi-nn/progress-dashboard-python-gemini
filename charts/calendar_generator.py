# charts/calendar_generator.py
import pandas as pd
from dash import html
from datetime import datetime, date, timedelta
import calendar
import dash_bootstrap_components as dbc
from dateutil.relativedelta import relativedelta # 追加

def create_html_calendar(acceptance_data, start_year_month, end_year_month): # 引数変更
    try:
        start_date = datetime.strptime(start_year_month, '%Y-%m').date().replace(day=1)
        end_date = datetime.strptime(end_year_month, '%Y-%m').date().replace(day=1)
    except (ValueError, TypeError):
        today = date.today()
        start_date = today.replace(day=1)
        # デフォルトで半年先まで表示する場合 (例)
        end_date = (start_date + relativedelta(months=+5)).replace(day=1)

    # --- データ準備 (変更なし) ---
    df = pd.DataFrame([
        {
            'id': r.get('id'), 'university_name': r.get('university_name'),
            'faculty_name': r.get('faculty_name'), 'department_name': r.get('department_name'),
            'exam_system': r.get('exam_system'), 'result': r.get('result'),
            'application_deadline': r.get('application_deadline'),
            'exam_date': r.get('exam_date'),
            'announcement_date': r.get('announcement_date'),
            'procedure_deadline': r.get('procedure_deadline')
        } for r in acceptance_data
    ])

    if df.empty:
        return html.Div(dbc.Alert("表示する受験・合否データがありません。", color="info"))

    date_cols = ['application_deadline', 'exam_date', 'announcement_date', 'procedure_deadline']
    dt_cols = ['app_deadline_dt', 'exam_dt', 'announcement_dt', 'proc_deadline_dt']

    for col, dt_col in zip(date_cols, dt_cols):
        if col in df.columns:
            df[dt_col] = pd.to_datetime(df[col], errors='coerce')
        else:
            df[dt_col] = pd.NaT

    sort_keys = [col for col in ['app_deadline_dt', 'exam_dt'] if col in df.columns]
    df_all_sorted = df.sort_values(by=sort_keys, ascending=True, na_position='last') if sort_keys else df

    # --- 複数月のカレンダーを生成 ---
    all_calendars_html = []
    current_month_date = start_date
    weekday_names_jp = ["月", "火", "水", "木", "金", "土", "日"]

    while current_month_date <= end_date:
        year, month = current_month_date.year, current_month_date.month
        _, num_days = calendar.monthrange(year, month)

        # --- 月ごとのヘッダー ---
        month_header = html.H5(f"{year}年 {month}月", className="text-center mt-4 mb-2 calendar-month-header")
        all_calendars_html.append(month_header)

        # --- テーブルヘッダー (各月) ---
        header_cells = [html.Th("大学・学部等", className="calendar-info-header-cell")]
        for day in range(1, num_days + 1):
            d = date(year, month, day)
            weekday_index = d.weekday()
            weekday_name = weekday_names_jp[weekday_index]
            cell_class = "calendar-header-cell"
            if weekday_index == 5: cell_class += " saturday"
            elif weekday_index == 6: cell_class += " sunday"
            header_cells.append(html.Th([str(day), html.Br(), weekday_name], className=cell_class, title=f"{year}-{month:02d}-{day:02d} ({weekday_name})"))

        # --- テーブルボディ (各月) ---
        body_rows = []
        for _, row in df_all_sorted.iterrows():
            # 情報セル (変更なし)
            info_parts = [
                html.Strong(f"{row.get('university_name','')} {row.get('faculty_name','') }"), html.Br(),
                row.get('department_name', ''), html.Br() if row.get('department_name') else '',
                html.Small(row.get('exam_system', ''), className="text-muted"),
            ]
            info_cell = html.Td(info_parts, className="calendar-info-cell")

            # 日付セル (変更なし、ただし対象月のみチェック)
            date_cells = []
            app_day = row['app_deadline_dt'].day if pd.notna(row.get('app_deadline_dt')) and row['app_deadline_dt'].year == year and row['app_deadline_dt'].month == month else None
            exam_day = row['exam_dt'].day if pd.notna(row.get('exam_dt')) and row['exam_dt'].year == year and row['exam_dt'].month == month else None
            announcement_day = row['announcement_dt'].day if pd.notna(row.get('announcement_dt')) and row['announcement_dt'].year == year and row['announcement_dt'].month == month else None
            proc_day = row['proc_deadline_dt'].day if pd.notna(row.get('proc_deadline_dt')) and row['proc_deadline_dt'].year == year and row['proc_deadline_dt'].month == month else None

            for day in range(1, num_days + 1):
                cell_classes = ["calendar-date-cell"]
                content = []
                title_texts = []
                current_date_obj = date(year, month, day)
                weekday_index = current_date_obj.weekday()
                if weekday_index == 5: cell_classes.append("saturday")
                elif weekday_index == 6: cell_classes.append("sunday")

                is_proc = proc_day is not None and day == proc_day
                is_announce = announcement_day is not None and day == announcement_day
                is_exam = exam_day is not None and day == exam_day
                is_app = app_day is not None and day == app_day

                if is_proc: cell_classes.append("proc-deadline-cell"); content.append("手"); title_texts.append("手続期日")
                if is_announce: cell_classes.append("announcement-date-cell"); content.append("合"); title_texts.append("発表日")
                if is_exam: cell_classes.append("exam-date-cell"); content.append("受") if "手" not in content and "合" not in content else None; title_texts.append("受験日")
                if is_app: cell_classes.append("app-deadline-cell"); content.append("出") if not content else None; title_texts.append("出願期日")

                final_content = "/".join(content) if content else ""
                final_title = ", ".join(title_texts) if title_texts else ""
                date_cells.append(html.Td(final_content, className=" ".join(cell_classes), title=final_title))

            body_rows.append(html.Tr([info_cell] + date_cells))

        # --- 月ごとのテーブル作成 ---
        calendar_table = html.Table(
            className="calendar-table",
            children=[
                html.Thead(html.Tr(header_cells)),
                html.Tbody(body_rows)
            ]
        )
        all_calendars_html.append(calendar_table)

        # 次の月へ
        current_month_date += relativedelta(months=+1)

    return html.Div(all_calendars_html, className="multi-month-calendar-wrapper") # 全体をDivで囲む