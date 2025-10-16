# charts/chart_generator.py

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import dcc

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

    Args:
        df: データフレーム
        title: グラフタイトル
        height: グラフの高さ（デフォルト250）
        for_print: 印刷用の場合True（レイアウトを調整）
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
            plot_total_duration = 0
        else:
            plot_total_duration = group_df['duration'].sum()

        fig.add_trace(go.Bar(
            y=['達成済'], x=[achieved_duration], name=group_name,
            orientation='h', marker=dict(color=color),
            legendgroup=group_name,
            hovertemplate=f"<b>{group_name}</b><br>達成済: {achieved_duration:.1f}h<extra></extra>"
        ))

        fig.add_trace(go.Bar(
            y=['予定'], x=[plot_total_duration], name=group_name,
            orientation='h', marker=dict(color=color, opacity=0.6),
            legendgroup=group_name, showlegend=False,
            hovertemplate=f"<b>{group_name}</b><br>総時間: {plot_total_duration:.1f}h<extra></extra>"
        ))

    # ★★★ 修正: 印刷用の設定を大幅に変更 ★★★
    if for_print:
        layout_config = {
            'barmode': 'stack',
            'title': {
                'text': title,
                'font': {'size': 14}  # タイトルサイズを小さく
            },
            'xaxis': {
                'title': "学習時間 (h)",
                'titlefont': {'size': 10},
                'tickfont': {'size': 9},
                'fixedrange': True,  # ズーム無効化
            },
            'yaxis': {
                'categoryorder': 'array',
                'categoryarray': ['予定', '達成済'],
                'tickfont': {'size': 10},
                'fixedrange': True,
            },
            'showlegend': False,
            'autosize': True,
            'width': None,  # 幅を自動調整
            'height': 250,  # 高さを少し抑える
            'margin': dict(t=40, l=50, r=10, b=35),  # マージンを最小化
            'paper_bgcolor': 'white',
            'plot_bgcolor': 'white',
        }
    else:
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

    # ★★★ 追加: 印刷用にグラフのサイズを固定 ★★★
    if for_print:
        fig.update_xaxes(automargin=True)
        fig.update_yaxes(automargin=True)

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

    liquid_color = "rgba(40, 167, 69, 0.7)"
    if achievement_rate < 20:
        liquid_color = "rgba(220, 53, 69, 0.7)"
    elif achievement_rate < 40:
        liquid_color = "rgba(255, 165, 0, 0.7)"
    elif achievement_rate < 60:
        liquid_color = "rgba(255, 193, 7, 0.7)"
    elif achievement_rate < 80:
        liquid_color = "rgba(177, 255, 47, 0.7)"

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=[subject], y=[100],
        marker_color='rgba(0,0,0,0.05)',
        hoverinfo='none',
        showlegend=False
    ))

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
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig