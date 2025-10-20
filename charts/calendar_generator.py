# charts/calendar_generator.py
import pandas as pd
from dash import html
from datetime import datetime, date, timedelta
import calendar
import dash_bootstrap_components as dbc
from dateutil.relativedelta import relativedelta

def create_single_month_table(acceptance_data_df, year, month):
    """指定された年月の単一カレンダーテーブルHTMLを生成する"""
    _, num_days = calendar.monthrange(year, month)
    weekday_names_jp = ["月", "火", "水", "木", "金", "土", "日"]

    # --- テーブルヘッダー ---
    header_cells = [html.Th("大学・学部等", className="calendar-info-header-cell")]
    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        weekday_index = current_date.weekday()
        weekday_name = weekday_names_jp[weekday_index]
        cell_class = "calendar-header-cell"
        if weekday_index == 5: cell_class += " saturday"
        elif weekday_index == 6: cell_class += " sunday"
        # 日付と曜日を表示
        header_cells.append(html.Th([str(day), html.Br(), weekday_name], className=cell_class, title=f"{year}-{month:02d}-{day:02d} ({weekday_name})"))

    # --- テーブルボディ ---
    body_rows = []
    # データがない場合も空のテーブルを表示するため、dfが空でもループは回さないがテーブル構造は作る
    if not acceptance_data_df.empty:
        for _, row in acceptance_data_df.iterrows():
            # 情報セル
            info_parts = [
                html.Strong(f"{row.get('university_name','')} {row.get('faculty_name','') }"), html.Br(),
                row.get('department_name', ''), html.Br() if row.get('department_name') else '',
                html.Small(row.get('exam_system', ''), className="text-muted"),
            ]
            info_cell = html.Td(info_parts, className="calendar-info-cell")

            # 日付セル
            date_cells = []
            # .get() と pd.notna() で安全にアクセス
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
    # データがない場合もTbodyは必要
    table_body = html.Tbody(body_rows)


    # 月ごとのテーブル作成
    calendar_table = html.Table(
        className="calendar-table",
        children=[
            html.Thead(html.Tr(header_cells)),
            table_body # Tbodyを使用
        ]
    )
    # 月ヘッダーとテーブルをDivで囲む
    return html.Div([
        # 月ヘッダーをテーブルキャプションに変更
        # html.H5(f"{year}年 {month}月", className="text-center calendar-month-header"), # H5削除
        calendar_table
    ], className="single-month-wrapper mb-4") # ラッパークラスとマージン追加


def create_html_calendar(acceptance_data, start_year_month, end_year_month):
    try:
        start_date = datetime.strptime(start_year_month, '%Y-%m').date().replace(day=1)
        # end_date の計算は create_single_month_table を呼び出すループで使用
    except (ValueError, TypeError):
        today = date.today()
        current_year = today.year
        start_date = date(current_year, 12, 1) # 当年12月開始

    # --- データ準備 (変更なし) ---
    df = pd.DataFrame([
        {'id': r.get('id'), 'university_name': r.get('university_name'),
         'faculty_name': r.get('faculty_name'), 'department_name': r.get('department_name'),
         'exam_system': r.get('exam_system'), 'result': r.get('result'),
         'application_deadline': r.get('application_deadline'), 'exam_date': r.get('exam_date'),
         'announcement_date': r.get('announcement_date'), 'procedure_deadline': r.get('procedure_deadline')}
        for r in acceptance_data
    ])
    # データがない場合のアラート表示
    if df.empty:
        return html.Div(dbc.Alert("表示する受験・合否データがありません。", color="info"))

    date_cols = ['application_deadline', 'exam_date', 'announcement_date', 'procedure_deadline']
    dt_cols = ['app_deadline_dt', 'exam_dt', 'announcement_dt', 'proc_deadline_dt']
    for col, dt_col in zip(date_cols, dt_cols):
        if col in df.columns: df[dt_col] = pd.to_datetime(df[col], errors='coerce')
        else: df[dt_col] = pd.NaT

    # --- ソートキーに大学名、学部名も追加して安定させる ---
    sort_keys = []
    if 'app_deadline_dt' in df.columns: sort_keys.append('app_deadline_dt')
    if 'exam_dt' in df.columns: sort_keys.append('exam_dt')
    # 大学名、学部名を追加
    sort_keys.extend(['university_name', 'faculty_name'])
    # --- ここまで変更 ---

    # na_position='last' で日付未入力のものを最後に回す
    df_all_sorted = df.sort_values(by=sort_keys, ascending=True, na_position='last') if sort_keys else df


    # --- 4ヶ月分のカレンダーHTMLを生成し、リストに格納 ---
    all_month_tables_html = []
    current_month_loop = start_date
    for i in range(4): # 12月, 1月, 2月, 3月
        year, month = current_month_loop.year, current_month_loop.month
        # 月ヘッダーを追加
        all_month_tables_html.append(html.H5(f"{year}年 {month}月", className="text-center calendar-month-header mt-4"))
        # その月のテーブルを追加
        all_month_tables_html.append(create_single_month_table(df_all_sorted, year, month))
        current_month_loop += relativedelta(months=+1)

    # --- 全体を一つのDivでラップして返す ---
    return html.Div(all_month_tables_html, className="multi-month-vertical-wrapper")