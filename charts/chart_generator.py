# charts/chart_generator.py

import pandas as pd
import plotly.graph_objects as go
from dash import dcc

def create_progress_stacked_bar_chart(df, title):
    """
    与えられたDataFrameから、参考書ごとの所要時間を積み上げた横棒グラフを生成する。
    Y軸は「達成済」と「予定」の2項目。
    """
    if df.empty:
        return None

    fig = go.Figure()
    
    # データを達成済と予定に分ける
    done_df = df[df['achieved_duration'] > 0]
    planned_df = df[df['planned_duration'] > 0]

    # 達成済のバーを参考書ごとに積み上げ
    for index, row in done_df.iterrows():
        fig.add_trace(go.Bar(
            y=['達成済'], x=[row['achieved_duration']], name=row['book_name'],
            orientation='h', marker=dict(color='mediumseagreen'),
            hovertemplate=f"{row['book_name']}: {row['achieved_duration']:.1f}h<extra></extra>"
        ))
        
    # 予定のバーを参考書ごとに積み上げ
    for index, row in planned_df.iterrows():
        fig.add_trace(go.Bar(
            y=['予定'], x=[row['planned_duration']], name=row['book_name'],
            orientation='h', marker=dict(color='cornflowerblue'),
            hovertemplate=f"{row['book_name']}: {row['planned_duration']:.1f}h<extra></extra>"
        ))

    fig.update_layout(
        barmode='stack', title_text=title, xaxis_title="真所要時間 (h)",
        showlegend=False, # 凡例は多すぎるので非表示
        margin=dict(t=80, b=40, l=10, r=10), height=250
    )
    return fig

def create_subject_progress_pie_chart(df, subject):
    """
    指定された科目の達成度を示す半円パイチャート（ゲージメーター）を生成する。
    真所要時間と達成割合を基に計算する。
    """
    subject_df = df[df['科目'] == subject].copy()
    
    subject_df['achieved_duration'] = subject_df['true_duration'] * (subject_df['completed_units'] / subject_df['total_units'])

    total_hours = subject_df['true_duration'].sum()
    done_hours = subject_df['achieved_duration'].sum()
    
    achievement_rate = (done_hours / total_hours * 100) if total_hours > 0 else 0
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=achievement_rate,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': subject, 'font': {'size': 20}},
        number={'suffix': "%", 'font': {'size': 28}},
        gauge={'axis': {'range': [None, 100]}, 'bar': {'color': "mediumseagreen"}}
    ))
    fig.update_layout(margin=dict(t=50, b=10, l=30, r=30), height=250)
    
    return dcc.Graph(
        figure=fig, 
        config={'displayModeBar': False},
        id={'type': 'subject-pie-chart', 'subject': subject}
    )