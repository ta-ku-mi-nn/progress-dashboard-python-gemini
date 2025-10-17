# charts/chart_generator.py

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import dcc
from datetime import datetime # datetime をインポート

def create_progress_chart(progress_data, subject):
    """
    特定の科目の進捗データから積み上げ棒グラフを生成する。
    """
    if not progress_data or subject not in progress_data:
        return go.Figure()

    subject_data = progress_data[subject]

    records = []
    for level, books in subject_data.items():
        for book_name, details in books.items():
            records.append({
                'level': level,
                'book_name': book_name,
                'duration': details.get('所要時間', 0),
                'is_planned': details.get('予定', False),
                'is_done': details.get('達成済', False),
                'completed_units': details.get('completed_units', 0),
                'total_units': details.get('total_units', 1),
            })

    if not records:
        return go.Figure()

    df = pd.DataFrame(records)

    df_planned = df[df['is_planned']].copy()

    if df_planned.empty:
        return go.Figure()

    df_planned['achieved_duration'] = df_planned.apply(
        lambda row: row['duration'] * (row['completed_units'] / row['total_units']) if row['total_units'] > 0 else 0,
        axis=1
    )
    df_planned['remaining_duration'] = df_planned['duration'] - df_planned['achieved_duration']

    fig = go.Figure()
    colors = px.colors.qualitative.Plotly

    for i, book in enumerate(df_planned['book_name'].unique()):
        book_df = df_planned[df_planned['book_name'] == book]
        color = colors[i % len(colors)]

        fig.add_trace(go.Bar(
            y=['進捗'],
            x=book_df['achieved_duration'],
            name=book,
            orientation='h',
            marker=dict(color=color),
            customdata=book_df[['duration']],
            hovertemplate=(
                f"<b>{book}</b><br>"
                "達成済: %{x:.1f}h<br>"
                "全体: %{customdata[0]:.1f}h<extra></extra>"
            )
        ))

        fig.add_trace(go.Bar(
            y=['進捗'],
            x=book_df['remaining_duration'],
            name=book,
            orientation='h',
            marker=dict(color=color, opacity=0.3),
            customdata=book_df[['duration']],
            hovertemplate=(
                f"<b>{book}</b><br>"
                "残り: %{x:.1f}h<br>"
                "全体: %{customdata[0]:.1f}h<extra></extra>"
            ),
            showlegend=False
        ))

    fig.update_layout(
        barmode='stack',
        title_text=f'<b>{subject}</b> の学習進捗',
        xaxis_title="学習時間 (h)",
        yaxis_title="",
        legend_title_text='参考書',
        height=300,
        margin=dict(t=50, l=10, r=10, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig

def create_progress_stacked_bar_chart(df, title, height=250, for_print=False):
    """
    与えられたDataFrameから、「予定」と「達成済」の2段積み上げ棒グラフを生成する。
    """
    if df.empty:
        return None

    df_planned = df[df['is_planned']].copy()
    if df_planned.empty:
        return None

    df_planned['achieved_duration'] = df_planned.apply(
        lambda row: row['duration'] * (row.get('completed_units', 0) / row.get('total_units', 1)) if row.get('total_units', 1) > 0 else 0,
        axis=1
    )

    fig = go.Figure()
    colors = px.colors.qualitative.Plotly

    group_key = 'subject' if 'subject' in df_planned.columns else 'book_name'

    for i, group_name in enumerate(df_planned[group_key].unique()):
        group_df = df_planned[df_planned[group_key] == group_name]
        color = colors[i % len(colors)]

        achieved_duration = group_df['achieved_duration'].sum()

        if group_name == '過去問':
            plot_total_duration = 0 # 過去問の場合は予定時間を0として扱う
        else:
            plot_total_duration = group_df['duration'].sum()

        # 達成済バー
        fig.add_trace(go.Bar(
            y=['達成済'], x=[achieved_duration], name=group_name,
            orientation='h', marker=dict(color=color),
            legendgroup=group_name,
            hovertemplate=f"<b>{group_name}</b><br>達成済: {achieved_duration:.1f}h<extra></extra>"
        ))

        # 予定バー (半透明)
        fig.add_trace(go.Bar(
            y=['予定'], x=[plot_total_duration], name=group_name,
            orientation='h', marker=dict(color=color, opacity=0.6),
            legendgroup=group_name, showlegend=False,
            hovertemplate=f"<b>{group_name}</b><br>総時間: {plot_total_duration:.1f}h<extra></extra>"
        ))

    if for_print:
        # 印刷用のレイアウト設定
        layout_config = {
            'barmode': 'stack',
            'title': {
                'text': title,
                'font': {'size': 14, 'color': 'black'}
            },
            'xaxis': {
                'title': {
                    'text': "学習時間 (h)",
                    'font': {'size': 11, 'color': 'black'}
                },
                'tickfont': {'size': 10, 'color': 'black'},
                'gridcolor': 'lightgray',
                'showgrid': True,
            },
            'yaxis': {
                'categoryorder': 'array',
                'categoryarray': ['予定', '達成済'],
                'tickfont': {'size': 11, 'color': 'black'},
            },
            'showlegend': False,
            'width': 650,
            'height': 250,
            'margin': dict(t=45, l=55, r=15, b=40),
            'paper_bgcolor': 'white',
            'plot_bgcolor': 'rgba(250,250,250,1)',
            'font': {'color': 'black'},
        }
    else:
        # 通常表示用のレイアウト設定
        layout_config = {
            'barmode': 'stack',
            'title_text': title,
            'xaxis_title': "学習時間 (h)",
            'yaxis': {'categoryorder':'array', 'categoryarray':['予定', '達成済']},
            'showlegend': False,
            'height': height,
            'margin': dict(t=50, l=60, r=20, b=40),
        }

    fig.update_layout(**layout_config)
    return fig

def create_subject_achievement_bar(df, subject):
    """
    指定された科目の達成度を示す液体タンク風の縦棒グラフのFigureを生成する。
    """
    subject_df = df[df['subject'] == subject].copy()

    subject_df['achieved_duration'] = subject_df.apply(
        lambda row: row['duration'] * (row.get('completed_units', 0) / row.get('total_units', 1)) if row.get('total_units', 1) > 0 else 0,
        axis=1
    )

    total_hours = subject_df[subject_df['is_planned']]['duration'].sum()
    done_hours = subject_df['achieved_duration'].sum()

    achievement_rate = (done_hours / total_hours * 100) if total_hours > 0 else 0

    liquid_color = "rgba(40, 167, 69, 0.7)" # 緑
    if achievement_rate < 20:
        liquid_color = "rgba(220, 53, 69, 0.7)" # 赤
    elif achievement_rate < 40:
        liquid_color = "rgba(255, 165, 0, 0.7)" # オレンジ系
    elif achievement_rate < 60:
        liquid_color = "rgba(255, 193, 7, 0.7)" # 黄
    elif achievement_rate < 80:
        liquid_color = "rgba(177, 255, 47, 0.7)" # 黄緑系

    fig = go.Figure()

    # 背景バー
    fig.add_trace(go.Bar(
        x=[subject], y=[100],
        marker_color='rgba(0,0,0,0.05)', # 薄いグレー
        hoverinfo='none',
        showlegend=False
    ))

    # 達成度バー
    fig.add_trace(go.Bar(
        x=[subject], y=[achievement_rate],
        marker_color=liquid_color,
        text=f"{achievement_rate:.1f}%",
        textposition='auto',
        textfont=dict(color='white', size=16),
        hoverinfo='none',
        showlegend=False
    ))

    fig.update_layout(
        title={
            'text': subject,
            'y':0.95, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top',
            'font': {'size': 20}
        },
        barmode='overlay',
        xaxis=dict(showticklabels=False),
        yaxis=dict(range=[0, 100], showticklabels=False, showgrid=False),
        margin=dict(t=50, b=20, l=10, r=10),
        height=220,
        paper_bgcolor='rgba(0,0,0,0)', # 背景透明
        plot_bgcolor='rgba(0,0,0,0)' # プロットエリア背景透明
    )

    return fig

def create_level_statistics_chart(stats_data, subject):
    """
    科目ごとのレベル達成人数を示す棒グラフを生成する。
    """
    if not stats_data or subject not in stats_data:
        fig = go.Figure()
        fig.update_layout(
            title=f'<b>{subject}</b> のレベル達成状況',
            annotations=[{
                'text': 'データがありません',
                'xref': 'paper', 'yref': 'paper',
                'x': 0.5, 'y': 0.5, 'showarrow': False
            }]
        )
        return fig

    subject_data = stats_data[subject]
    levels = ['日大', 'MARCH', '早慶']
    counts = [subject_data.get(level, 0) for level in levels]

    fig = go.Figure(data=[
        go.Bar(
            x=levels,
            y=counts,
            text=counts,
            textposition='auto',
            marker_color=['#0d6efd', '#ffc107', '#dc3545'] # レベルごとの色
        )
    ])

    fig.update_layout(
        title_text=f'<b>{subject}</b> のレベル達成人数',
        xaxis_title="レベル",
        yaxis_title="生徒数",
        height=400,
        margin=dict(t=50, l=10, r=10, b=30),
    )

    return fig

def create_acceptance_gantt_chart(acceptance_data):
    """
    大学合否データからガントチャートを生成する。
    受験日から合格発表日までを期間として表示する。
    """
    if not acceptance_data:
        fig = go.Figure()
        fig.update_layout(
            title="受験スケジュール",
            annotations=[{
                'text': '合否データがありません',
                'xref': 'paper', 'yref': 'paper',
                'x': 0.5, 'y': 0.5, 'showarrow': False
            }]
        )
        return fig

    df = pd.DataFrame(acceptance_data)

    # 有効な日付データのみを抽出
    df_filtered = df.dropna(subset=['exam_date', 'announcement_date'])
    if df_filtered.empty:
        fig = go.Figure()
        fig.update_layout(
            title="受験スケジュール",
            annotations=[{
                'text': '有効な受験日・発表日データがありません',
                'xref': 'paper', 'yref': 'paper',
                'x': 0.5, 'y': 0.5, 'showarrow': False
            }]
        )
        return fig

    # 日付文字列をdatetimeオブジェクトに変換し、無効なものは除外
    valid_data = []
    for _, row in df_filtered.iterrows():
        try:
            start_date = pd.to_datetime(row['exam_date'])
            end_date = pd.to_datetime(row['announcement_date'])
            # 発表日 >= 受験日 であることを確認
            if end_date >= start_date:
                 # 期間が0日の場合、表示上少しだけ期間を持たせる（例: 12時間）
                 if end_date == start_date:
                     end_date = start_date + pd.Timedelta(hours=12)

                 task_label = f"{row['university_name']} {row['faculty_name']}"
                 if row.get('department_name'):
                     task_label += f" {row['department_name']}"
                 valid_data.append({
                     'Task': task_label,
                     'Start': start_date,
                     'Finish': end_date,
                     'University': row['university_name'], # 色分け用
                     'Result': row.get('result', '未定') # ホバー表示用
                 })
        except (ValueError, TypeError):
            continue # 変換できない日付はスキップ

    if not valid_data:
        fig = go.Figure()
        fig.update_layout(
            title="受験スケジュール",
            annotations=[{
                'text': '表示可能な日付データがありません',
                'xref': 'paper', 'yref': 'paper',
                'x': 0.5, 'y': 0.5, 'showarrow': False
            }]
        )
        return fig

    df_gantt = pd.DataFrame(valid_data)
    # 開始日でソートして表示順を整理
    df_gantt = df_gantt.sort_values(by='Start')

    fig = px.timeline(
        df_gantt,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="University", # 大学ごとに色分け
        title="受験スケジュール",
        hover_data=['Result'] # ホバー時に合否結果も表示
    )

    fig.update_yaxes(categoryorder='array', categoryarray=df_gantt['Task'].tolist()) # ソート順を維持

    fig.update_layout(
        xaxis_title="日付",
        yaxis_title="大学・学部",
        legend_title="大学名",
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis_range=[df_gantt['Start'].min() - pd.Timedelta(days=3), # 開始日の少し前から
                     df_gantt['Finish'].max() + pd.Timedelta(days=3)] # 終了日の少し後まで表示
    )

    return fig