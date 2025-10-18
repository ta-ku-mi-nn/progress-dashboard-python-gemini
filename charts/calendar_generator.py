# charts/calendar_generator.py

import pandas as pd
from dash import html
from datetime import datetime, date, timedelta
import calendar
import dash_bootstrap_components as dbc

def create_html_calendar(acceptance_data, target_year_month):
    """
    指定された年月のカレンダーHTML構造を生成する。
    左側に大学情報列を追加し、受験日と発表日を色付けする。
    表示月の予定有無に関わらず、全合否データを左列に表示する。
    target_year_month: 'YYYY-MM' 形式の文字列
    """
    try:
        target_date = datetime.strptime(target_year_month, '%Y-%m')
        year, month = target_date.year, target_date.month
    except (ValueError, TypeError):
        today = date.today()
        year, month = today.year, today.month
        target_year_month = today.strftime('%Y-%m') # target_year_month を設定

    # その月の日数を取得
    _, num_days = calendar.monthrange(year, month)
    # 曜日名リスト (日本語)
    weekday_names_jp = ["月", "火", "水", "木", "金", "土", "日"]

    # --- テーブルヘッダー (情報列 + 日付と曜日) ---
    header_cells = [html.Th("大学・学部等", className="calendar-info-header-cell")]
    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        weekday_index = current_date.weekday() # 0:月, 6:日
        weekday_name = weekday_names_jp[weekday_index]
        cell_class = "calendar-header-cell"
        if weekday_index == 5: # 土曜日
            cell_class += " saturday"
        elif weekday_index == 6: # 日曜日
            cell_class += " sunday"
        header_cells.append(html.Th([str(day), html.Br(), weekday_name], className=cell_class, title=f"{year}-{month:02d}-{day:02d} ({weekday_name})"))

    # --- テーブルボディ (イベントごとに1行) ---
    body_rows = []
    df = pd.DataFrame(acceptance_data)
    # 日付列をdatetimeオブジェクトに変換（変換できないものはNaT）
    df['app_deadline_dt'] = pd.to_datetime(df['application_deadline'], errors='coerce') # ★追加
    df['exam_dt'] = pd.to_datetime(df['exam_date'], errors='coerce')
    df['announcement_dt'] = pd.to_datetime(df['announcement_date'], errors='coerce')
    df['proc_deadline_dt'] = pd.to_datetime(df['procedure_deadline'], errors='coerce') # ★追加


    # 受験日でソート (受験日がないものは最後に)
    # ソートキーに application_deadline も追加（出願日が早い順）
    df_all_sorted = df.sort_values(by=['app_deadline_dt', 'exam_dt'], ascending=True, na_position='last')

    if df_all_sorted.empty:
        return html.Div(dbc.Alert("表示する受験・合否データがありません。", color="info"))

    for _, row in df_all_sorted.iterrows():
        # --- 1列目: 大学情報セル (変更なし) ---
        info_parts = [
            html.Strong(f"{row['university_name']} {row['faculty_name']}"),
            html.Br(),
            row.get('department_name', ''),
            html.Br() if row.get('department_name') else '',
            html.Small(row.get('exam_system', ''), className="text-muted"),
        ]
        info_cell = html.Td(info_parts, className="calendar-info-cell")

        # --- 2列目以降: 日付セル ---
        date_cells = []
        # 日付が「表示月」に含まれるかチェックする
        app_day = row['app_deadline_dt'].day if pd.notna(row['app_deadline_dt']) and row['app_deadline_dt'].year == year and row['app_deadline_dt'].month == month else None # ★追加
        exam_day = row['exam_dt'].day if pd.notna(row['exam_dt']) and row['exam_dt'].year == year and row['exam_dt'].month == month else None
        announcement_day = row['announcement_dt'].day if pd.notna(row['announcement_dt']) and row['announcement_dt'].year == year and row['announcement_dt'].month == month else None
        proc_day = row['proc_deadline_dt'].day if pd.notna(row['proc_deadline_dt']) and row['proc_deadline_dt'].year == year and row['proc_deadline_dt'].month == month else None # ★追加

        for day in range(1, num_days + 1):
            cell_classes = ["calendar-date-cell"] # ★リストに変更
            content = []
            title_texts = []
            current_date_obj = date(year, month, day)
            weekday_index = current_date_obj.weekday()

            if weekday_index == 5: cell_classes.append("saturday") # ★リストに追加
            elif weekday_index == 6: cell_classes.append("sunday") # ★リストに追加

            # 各日付のチェックとクラス・コンテンツ追加
            is_proc = proc_day is not None and day == proc_day
            is_announce = announcement_day is not None and day == announcement_day
            is_exam = exam_day is not None and day == exam_day
            is_app = app_day is not None and day == app_day

            # 優先度: 手続 > 発表 > 受験 > 出願 (クラスと文字)
            if is_proc:
                cell_classes.append("proc-deadline-cell") # ★追加
                content.append("手")
                title_texts.append("手続期日")
            if is_announce:
                cell_classes.append("announcement-date-cell") # 既存
                content.append("合")
                title_texts.append("発表日")
            if is_exam:
                cell_classes.append("exam-date-cell") # 既存
                if "手" not in content and "合" not in content and "否" not in content and "？" not in content: # 上位がなければ表示
                    content.append("受")
                title_texts.append("受験日")
            if is_app:
                cell_classes.append("app-deadline-cell") # ★追加
                if not content: # まだ何もなければ表示
                    content.append("出")
                title_texts.append("出願期日")


            # コンテンツがあれば結合してセルに追加
            final_content = "/".join(content) if content else ""
            final_title = ", ".join(title_texts) if title_texts else ""
            # ★クラス名をスペースで結合して設定
            date_cells.append(html.Td(final_content, className=" ".join(cell_classes), title=final_title))
        # --- ★★★ ここまで修正 ★★★ ---

        body_rows.append(html.Tr([info_cell] + date_cells))

    # テーブル構造を組み立て
    calendar_table = html.Table(
        className="calendar-table",
        children=[
            html.Thead(html.Tr(header_cells)),
            html.Tbody(body_rows)
        ]
    )

    return calendar_table