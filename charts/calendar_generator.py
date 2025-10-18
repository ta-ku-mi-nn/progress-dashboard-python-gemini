# charts/calendar_generator.py

import pandas as pd
from dash import html
from datetime import datetime, date, timedelta
import calendar
import dash_bootstrap_components as dbc

def create_html_calendar(acceptance_data, target_year_month):
    # --- 年月取得 (変更なし) ---
    try:
        target_date = datetime.strptime(target_year_month, '%Y-%m')
        year, month = target_date.year, target_date.month
    except (ValueError, TypeError):
        today = date.today()
        year, month = today.year, today.month
        target_year_month = today.strftime('%Y-%m') # target_year_month を設定

    _, num_days = calendar.monthrange(year, month)
    weekday_names_jp = ["月", "火", "水", "木", "金", "土", "日"]

    # --- テーブルヘッダー (変更なし) ---
    header_cells = [html.Th("大学・学部等", className="calendar-info-header-cell")]
    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        weekday_index = current_date.weekday()
        weekday_name = weekday_names_jp[weekday_index]
        cell_class = "calendar-header-cell"
        if weekday_index == 5: cell_class += " saturday"
        elif weekday_index == 6: cell_class += " sunday"
        header_cells.append(html.Th([str(day), html.Br(), weekday_name], className=cell_class, title=f"{year}-{month:02d}-{day:02d} ({weekday_name})"))

    # --- テーブルボディ ---
    body_rows = []
    # ↓↓↓ .get() を使って安全にDataFrameを作成 ↓↓↓
    df = pd.DataFrame([
        {
            'id': r.get('id'),
            'university_name': r.get('university_name'),
            'faculty_name': r.get('faculty_name'),
            'department_name': r.get('department_name'),
            'exam_system': r.get('exam_system'),
            'result': r.get('result'),
            'application_deadline': r.get('application_deadline'), # .get()を使用
            'exam_date': r.get('exam_date'),
            'announcement_date': r.get('announcement_date'),
            'procedure_deadline': r.get('procedure_deadline') # .get()を使用
        } for r in acceptance_data
    ])
    # ↑↑↑ 修正ここまで ↑↑↑

    if df.empty:
         return html.Div(dbc.Alert("表示する受験・合否データがありません。", color="info"))

    # 日付列をdatetimeオブジェクトに変換（変換できないものはNaT）
    # ↓↓↓ 列が存在するか確認してから変換 ↓↓↓
    if 'application_deadline' in df.columns:
        df['app_deadline_dt'] = pd.to_datetime(df['application_deadline'], errors='coerce')
    else:
        df['app_deadline_dt'] = pd.NaT # 列がない場合はNaTで埋める

    if 'exam_date' in df.columns:
        df['exam_dt'] = pd.to_datetime(df['exam_date'], errors='coerce')
    else:
        df['exam_dt'] = pd.NaT

    if 'announcement_date' in df.columns:
        df['announcement_dt'] = pd.to_datetime(df['announcement_date'], errors='coerce')
    else:
        df['announcement_dt'] = pd.NaT

    if 'procedure_deadline' in df.columns:
        df['proc_deadline_dt'] = pd.to_datetime(df['procedure_deadline'], errors='coerce')
    else:
        df['proc_deadline_dt'] = pd.NaT
    # ↑↑↑ 修正ここまで ↑↑↑

    # ソートキーに application_deadline も追加（出願日が早い順）
    # ↓↓↓ ソートキーが存在するか確認してからソート ↓↓↓
    sort_keys = []
    # DataFrameのカラムとして存在するかどうかをチェック
    if 'app_deadline_dt' in df.columns:
        sort_keys.append('app_deadline_dt')
    if 'exam_dt' in df.columns:
        sort_keys.append('exam_dt')

    if sort_keys: # ソートキーが1つ以上あればソート実行
        df_all_sorted = df.sort_values(by=sort_keys, ascending=True, na_position='last')
    else: # ソートキーがなければソートしない
        df_all_sorted = df
    # ↑↑↑ 修正ここまで ↑↑↑


    for _, row in df_all_sorted.iterrows():
        # --- 1列目: 大学情報セル (安全アクセスに変更) ---
        info_parts = [
            html.Strong(f"{row.get('university_name','')} {row.get('faculty_name','') }"), # .get()を使用
            html.Br(),
            row.get('department_name', ''),
            html.Br() if row.get('department_name') else '',
            html.Small(row.get('exam_system', ''), className="text-muted"),
        ]
        info_cell = html.Td(info_parts, className="calendar-info-cell")

        # --- 2列目以降: 日付セル (安全アクセスに変更) ---
        date_cells = []
        # ↓↓↓ .get() と pd.notna() で安全にアクセス ↓↓↓
        app_day = row['app_deadline_dt'].day if pd.notna(row.get('app_deadline_dt')) and row['app_deadline_dt'].year == year and row['app_deadline_dt'].month == month else None
        exam_day = row['exam_dt'].day if pd.notna(row.get('exam_dt')) and row['exam_dt'].year == year and row['exam_dt'].month == month else None
        announcement_day = row['announcement_dt'].day if pd.notna(row.get('announcement_dt')) and row['announcement_dt'].year == year and row['announcement_dt'].month == month else None
        proc_day = row['proc_deadline_dt'].day if pd.notna(row.get('proc_deadline_dt')) and row['proc_deadline_dt'].year == year and row['proc_deadline_dt'].month == month else None
        # ↑↑↑ 修正ここまで ↑↑↑

        # --- 日付セルの生成ループ (変更なし) ---
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

             # 優先度: 手続 > 発表 > 受験 > 出願 (クラスと文字)
             if is_proc:
                 cell_classes.append("proc-deadline-cell")
                 content.append("手")
                 title_texts.append("手続期日")
             if is_announce:
                 cell_classes.append("announcement-date-cell")
                 content.append("合")
                 title_texts.append("発表日")
             if is_exam:
                 cell_classes.append("exam-date-cell")
                 if "手" not in content and "合" not in content: # 上位がなければ表示
                     content.append("受")
                 title_texts.append("受験日")
             if is_app:
                 cell_classes.append("app-deadline-cell")
                 if not content: # まだ何もなければ表示
                     content.append("出")
                 title_texts.append("出願期日")

             final_content = "/".join(content) if content else ""
             final_title = ", ".join(title_texts) if title_texts else ""
             date_cells.append(html.Td(final_content, className=" ".join(cell_classes), title=final_title))

        body_rows.append(html.Tr([info_cell] + date_cells))

    # --- テーブル構造 (変更なし) ---
    calendar_table = html.Table(
        className="calendar-table",
        children=[
            html.Thead(html.Tr(header_cells)),
            html.Tbody(body_rows)
        ]
    )

    return calendar_table