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
    header_cells = [html.Th("大学・学部等", className="calendar-info-header-cell")] # 情報列ヘッダーを追加
    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        weekday_index = current_date.weekday() # 0:月, 6:日
        weekday_name = weekday_names_jp[weekday_index]
        cell_class = "calendar-header-cell"
        if weekday_index == 5: # 土曜日
            cell_class += " saturday"
        elif weekday_index == 6: # 日曜日
            cell_class += " sunday"
        # ツールチップに曜日も表示
        header_cells.append(html.Th([str(day), html.Br(), weekday_name], className=cell_class, title=f"{year}-{month:02d}-{day:02d} ({weekday_name})"))

    # --- テーブルボディ (イベントごとに1行) ---
    body_rows = []
    df = pd.DataFrame(acceptance_data)
    # 日付列をdatetimeオブジェクトに変換（変換できないものはNaT）
    df['exam_dt'] = pd.to_datetime(df['exam_date'], errors='coerce')
    df['announcement_dt'] = pd.to_datetime(df['announcement_date'], errors='coerce')

    # 表示月に関連するデータのみフィルタリングし、受験日でソート
    df_month_related = df[
        ((df['exam_dt'].dt.year == year) & (df['exam_dt'].dt.month == month)) |
        ((df['announcement_dt'].dt.year == year) & (df['announcement_dt'].dt.month == month))
    ].sort_values(by='exam_dt', ascending=True, na_position='last')


    if df_month_related.empty:
        return html.Div(dbc.Alert("表示する受験・合否データがありません。", color="info"))

    for _, row in df_month_related.iterrows():
        # --- 1列目: 大学情報セル ---
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
        exam_day = row['exam_dt'].day if pd.notna(row['exam_dt']) and row['exam_dt'].year == year and row['exam_dt'].month == month else None
        announcement_day = row['announcement_dt'].day if pd.notna(row['announcement_dt']) and row['announcement_dt'].year == year and row['announcement_dt'].month == month else None

        for day in range(1, num_days + 1):
            cell_class = "calendar-date-cell"
            content = ""
            title_text = "" # ツールチップ用テキスト
            current_date_obj = date(year, month, day)
            weekday_index = current_date_obj.weekday()

            if weekday_index == 5: cell_class += " saturday"
            elif weekday_index == 6: cell_class += " sunday"

            if day == exam_day:
                cell_class += " exam-date-cell"
                content = "📝" # アイコン表示
                title_text = "受験日"
            if day == announcement_day:
                # 発表日は色を優先し、既存の色クラスがあれば上書き
                cell_class = cell_class.replace(" exam-date-cell", "") # 受験日と重なる場合、発表日を優先
                cell_class += " announcement-date-cell"
                result_text = row.get('result', '未定')
                result_icon = "🎉" if result_text == '合格' else ("❌" if result_text == '不合格' else "❓")
                content = result_icon # アイコン表示
                title_text = f"発表日 ({result_text})"

            # 今日の日付を強調表示 (オプション)
            # if date(year, month, day) == date.today():
            #    cell_class += " today-cell"

            date_cells.append(html.Td(content, className=cell_class, title=title_text))

        body_rows.append(html.Tr([info_cell] + date_cells))

    # テーブル構造を組み立て
    calendar_table = html.Table(
        className="calendar-table", # 新しいクラス名に変更
        children=[
            html.Thead(html.Tr(header_cells)),
            html.Tbody(body_rows)
        ]
    )

    return calendar_table