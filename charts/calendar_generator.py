# charts/calendar_generator.py (新規作成)

import pandas as pd
from dash import html
from datetime import datetime, date, timedelta
import calendar
import dash_bootstrap_components as dbc

def create_html_calendar(acceptance_data, target_year_month):
    """
    指定された年月の横一列カレンダーHTML構造を生成する。
    target_year_month: 'YYYY-MM' 形式の文字列
    """
    try:
        target_date = datetime.strptime(target_year_month, '%Y-%m')
        year, month = target_date.year, target_date.month
    except (ValueError, TypeError):
        today = date.today()
        year, month = today.year, today.month

    # その月の日数を取得
    _, num_days = calendar.monthrange(year, month)
    # 曜日名リスト (日本語)
    weekday_names_jp = ["月", "火", "水", "木", "金", "土", "日"]

    # イベントデータを日付ごとに集約
    events_by_date = {}
    df = pd.DataFrame(acceptance_data)
    df['exam_dt'] = pd.to_datetime(df['exam_date'], errors='coerce')
    df['announcement_dt'] = pd.to_datetime(df['announcement_date'], errors='coerce')

    for _, row in df.iterrows():
        # 受験日イベント
        if pd.notna(row['exam_dt']) and row['exam_dt'].year == year and row['exam_dt'].month == month:
            day = row['exam_dt'].day
            event_text = f"📝 {row['university_name']}" # 短縮表示
            if day not in events_by_date: events_by_date[day] = []
            # ツールチップ用に詳細情報を保持 (オプション)
            tooltip_text = f"受験: {row['university_name']} {row['faculty_name']}"
            if row.get('department_name'): tooltip_text += f" {row['department_name']}"
            if row.get('exam_system'): tooltip_text += f" ({row['exam_system']})"
            events_by_date[day].append(html.Span(event_text, className="event event-exam", title=tooltip_text))
        # 発表日イベント
        if pd.notna(row['announcement_dt']) and row['announcement_dt'].year == year and row['announcement_dt'].month == month:
            day = row['announcement_dt'].day
            result_text = row.get('result', '未定')
            result_icon = "🎉" if result_text == '合格' else ("❌" if result_text == '不合格' else "❓")
            event_text = f"{result_icon} {row['university_name']}" # 短縮表示
            event_class = "event event-pass" if result_text == '合格' else ("event event-fail" if result_text == '不合格' else "event event-pending")
            # ツールチップ用に詳細情報を保持 (オプション)
            tooltip_text = f"発表: {row['university_name']} {row['faculty_name']} - {result_text}"
            if row.get('department_name'): tooltip_text += f" {row['department_name']}"
            if row.get('exam_system'): tooltip_text += f" ({row['exam_system']})"
            if day not in events_by_date: events_by_date[day] = []
            events_by_date[day].append(html.Span(event_text, className=event_class, title=tooltip_text))

    # --- テーブルヘッダー (日付と曜日) ---
    header_cells = []
    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        weekday_index = current_date.weekday() # 0:月, 6:日
        weekday_name = weekday_names_jp[weekday_index]
        cell_class = "calendar-header-cell"
        if weekday_index == 5: # 土曜日
            cell_class += " saturday"
        elif weekday_index == 6: # 日曜日
            cell_class += " sunday"
        header_cells.append(html.Th([str(day), html.Br(), weekday_name], className=cell_class))

    # --- テーブルボディ (イベント表示用) ---
    event_cells = []
    max_events_per_day = 4 # 1日に表示するイベントの最大行数 (調整可能)
    for day in range(1, num_days + 1):
        current_date = date(year, month, day)
        weekday_index = current_date.weekday()
        cell_class = "calendar-event-cell"
        if weekday_index == 5: cell_class += " saturday"
        elif weekday_index == 6: cell_class += " sunday"

        day_events = events_by_date.get(day, [])
        # 最大行数を超えるイベントは表示しない
        cell_content = [html.Div(event, className="event-item") for event in day_events[:max_events_per_day]]
        # 高さを揃えるために、空のDivを追加 (最大行数まで)
        for _ in range(max_events_per_day - len(cell_content)):
             cell_content.append(html.Div(html.Br(), className="event-item-placeholder")) # 改行で高さを確保

        event_cells.append(html.Td(cell_content, className=cell_class))

    # テーブル構造を組み立て
    calendar_table = html.Table(
        className="horizontal-calendar",
        children=[
            html.Thead(html.Tr(header_cells)),
            html.Tbody(html.Tr(event_cells))
        ]
    )

    # データがない場合はメッセージを表示
    if not acceptance_data:
        return html.Div(dbc.Alert("表示する受験・合否データがありません。", color="info"))

    return calendar_table