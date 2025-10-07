# charts/chart_generator.py

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px # ★★★ Plotly Express をインポート ★★★
from dash import dcc

def create_progress_stacked_bar_chart(df, title):
    """
    与えられたDataFrameから、積み上げ棒グラフを生成する。
    - 「達成済」バー：現在までに完了した総学習時間
    - 「予定」バー：計画されている総学習時間（完了分＋未達成分）
    - 参考書ごとにカラーパレットで色分けする
    """
    if df.empty:
        return None

    # 関数内で時間の計算を行う
    df['achieved_duration'] = df.apply(
        lambda row: row['true_duration'] * (row['completed_units'] / row['total_units']) if row.get('total_units', 1) > 0 else 0,
        axis=1
    )
    
    fig = go.Figure()
    
    # ★★★ カラーパレットを定義 ★★★
    colors = px.colors.qualitative.Plotly
    
    # ★★★ 新しいロジックでグラフを構築 ★★★
    for i, row in df.iterrows():
        color = colors[i % len(colors)] # カラーパレットを順番に使用

        # 1. 「達成済」バーに、各参考書の達成済み時間を追加
        if row['achieved_duration'] > 0.1:
            fig.add_trace(go.Bar(
                y=['達成済'],
                x=[row['achieved_duration']],
                name=row['book_name'],
                orientation='h',
                marker=dict(color=color),
                hovertemplate=f"<b>{row['book_name']}</b><br>達成済: {row['achieved_duration']:.1f}h<extra></extra>",
                legendgroup=row['book_name'], # 凡例のグループ化
                showlegend=False # 凡例は非表示
            ))
            
        # 2. 「予定」バーに、各参考書の総時間を追加
        if row['true_duration'] > 0.1:
            fig.add_trace(go.Bar(
                y=['予定'],
                x=[row['true_duration']],
                name=row['book_name'],
                orientation='h',
                marker=dict(color=color, opacity=0.6), # 予定バーは少し薄くする
                hovertemplate=f"<b>{row['book_name']}</b><br>総時間: {row['true_duration']:.1f}h<extra></extra>",
                legendgroup=row['book_name'], # 凡例のグループ化
                showlegend=False # 凡例は非表示
            ))

    fig.update_layout(
        barmode='stack',
        title_text=title,
        xaxis_title="真所要時間 (h)",
        margin=dict(t=80, b=40, l=60, r=10),
        height=250,
        yaxis={'categoryorder':'array', 'categoryarray':['予定', '達成済']}
    )
    return fig


def create_subject_progress_pie_chart(df, subject):
    """
    指定された科目の達成度を示す半円パイチャート（ゲージメーター）を生成する。
    真所要時間と達成割合を基に計算する。
    """
    subject_df = df[df['科目'] == subject].copy()
    
    subject_df['achieved_duration'] = subject_df.apply(
        lambda row: row['true_duration'] * (row.get('completed_units', 0) / row.get('total_units', 1)) if row.get('total_units', 1) > 0 else 0,
        axis=1
    )

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