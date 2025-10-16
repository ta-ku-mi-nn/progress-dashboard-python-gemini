"""
グラフ生成関数
"""
import plotly.graph_objects as go
import plotly.express as px
from dash import html
import dash_bootstrap_components as dbc


def create_progress_bar_graph(_, __):
    """進捗バーグラフを作成"""
    # 実装は省略
    return go.Figure()


def create_completion_trend_chart(daily_data):
    """完了トレンドチャートを作成"""
    if daily_data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            showlegend=False
        )
        return fig

    fig = px.line(
        daily_data,
        x='日付',
        y='完了数',
        title='',
        markers=True,
        line_shape='spline'
    )

    fig.update_traces(
        line=dict(color='#3498db', width=3),
        marker=dict(size=8, color='#e74c3c')
    )

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial, sans-serif"),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
        margin=dict(l=40, r=40, t=40, b=40)
    )

    return fig

def create_daily_progress_chart(daily_data):
    """日別進捗バーチャートを作成"""
    if daily_data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=14)
        )
        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            showlegend=False
        )
        return fig

    colors = ['#e74c3c' if x == 0 else '#27ae60' for x in daily_data['完了数']]

    fig = go.Figure(data=[
        go.Bar(
            x=daily_data['日付'],
            y=daily_data['完了数'],
            marker_color=colors,
            text=daily_data['完了数'],
            textposition='auto'
        )
    ])

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial, sans-serif"),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
        margin=dict(l=40, r=40, t=40, b=40),
        showlegend=False
    )

    return fig

def create_textbook_progress_chart(textbook_data):
    """参考書別進捗チャートを作成"""
    if textbook_data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="データがありません",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            showlegend=False
        )
        return fig

    fig = go.Figure()

    # 完了数のバー
    fig.add_trace(go.Bar(
        name='完了数',
        x=textbook_data['参考書名'],
        y=textbook_data['完了数'],
        marker_color='#27ae60',
        text=textbook_data['完了数'],
        textposition='auto'
    ))

    # 未完了数のバー
    textbook_data['未完了数'] = textbook_data['総数'] - textbook_data['完了数']
    fig.add_trace(go.Bar(
        name='未完了数',
        x=textbook_data['参考書名'],
        y=textbook_data['未完了数'],
        marker_color='#e74c3c',
        text=textbook_data['未完了数'],
        textposition='auto'
    ))

    fig.update_layout(
        barmode='stack',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial, sans-serif"),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig

def create_subject_pie_charts(subject_data):
    """科目別液体タンクデザインを作成"""
    if subject_data.empty:
        return html.Div([
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className="fas fa-info-circle me-2 text-primary"),
                        "🚀 はじめての方へ"
                    ], className="mb-0 text-primary")
                ]),
                dbc.CardBody([
                    html.P("進捗データを表示するには、まず学習予定を設定する必要があります：", className="mb-3"),
                    html.Ol([
                        html.Li("左メニューの「進捗更新」ボタンをクリック"),
                        html.Li("勉強したい科目を選択"),
                        html.Li("参考書の「予定」にチェックを入れる"),
                        html.Li("進捗や達成状況を入力")
                    ], className="mb-3"),
                    dbc.Alert([
                        html.I(className="fas fa-lightbulb me-2"),
                        "まずは1つの科目から始めてみましょう！"
                    ], color="info", className="mb-0")
                ])
            ], className="shadow-sm")
        ])

    liquid_tanks = []
    for _, row in subject_data.iterrows():
        subject = row['科目']
        completed = row['完了数']
        total = row['総数']
        achievement_rate = row['平均達成率']

        # 達成率に応じた色設定
        if achievement_rate >= 80:
            liquid_color = "#28a745"  # 緑
            glow_color = "#28a745"
        elif achievement_rate >= 60:
            liquid_color = "#ffc107"  # 黄色
            glow_color = "#ffc107"
        elif achievement_rate >= 40:
            liquid_color = "#fd7e14"  # オレンジ
            glow_color = "#fd7e14"
        else:
            liquid_color = "#dc3545"  # 赤
            glow_color = "#dc3545"

        # 液体タンクカードを作成
        tank_card = dbc.Col([
                    # 液体タンクコンテナ
                    html.Div([
                        # タンク外枠
                        html.Div([
                            # 液体部分
                            html.Div([
                                # 液体の波エフェクト
                                html.Div(className="wave"),
                                html.Div(className="wave wave2"),
                            ], style={
                                'height': f'{achievement_rate}%',
                                'width': '100%',
                                'backgroundColor': liquid_color,
                                'position': 'absolute',
                                'bottom': '0',
                                'borderRadius': '0 0 15px 15px',
                                'transition': 'all 0.5s ease',
                                'overflow': 'hidden'
                            }),
                            # 科目名と達成率（タンク内）
                            html.Div([
                                html.H4(subject, className="text-white fw-bold mb-2",
                                       style={'textShadow': '3px 3px 6px rgba(0,0,0,0.7)', 'fontSize': '1.3rem'}),
                                html.H2(f"{achievement_rate:.1f}%", className="text-white fw-bold mb-0",
                                       style={'textShadow': '3px 3px 6px rgba(0,0,0,0.7)', 'fontSize': '2.2rem'})
                            ], style={
                                'position': 'absolute',
                                'top': '50%',
                                'left': '50%',
                                'transform': 'translate(-50%, -50%)',
                                'textAlign': 'center',
                                'zIndex': '10'
                            }),
                            # 詳細ボタン
                            dbc.Button(
                                html.I(className="fas fa-eye"),
                                id={'type': 'subject-overlay', 'index': subject},
                                color="light",
                                size="sm",
                                className="position-absolute",
                                style={
                                    'top': '10px',
                                    'right': '10px',
                                    'zIndex': '20',
                                    'opacity': '0.8',
                                    'borderRadius': '50%',
                                    'width': '35px',
                                    'height': '35px'
                                },
                                title="詳細を表示"
                            )
                        ], style={
                            'width': '100%',
                            'height': '200px',
                            'border': f'4px solid {liquid_color}',
                            'borderRadius': '20px',
                            'position': 'relative',
                            'overflow': 'hidden',
                            'backgroundColor': '#f8f9fa',
                            'boxShadow': f'0 0 25px {glow_color}50'
                        })
                    ], className="mb-2"),
                    # 進捗情報
                    html.Div([
                        html.I(className="fas fa-book me-2", style={'color': liquid_color}),
                        html.Span(f"{completed}/{total} 完了", className="fw-bold"),
                        html.Br(),
                        html.Small("総合進捗率", className="text-muted")
                    ], className="text-center mt-2")
            ], className="h-100 shadow-lg", style={
                'transition': 'transform 0.2s ease, box-shadow 0.2s ease',
                'cursor': 'pointer',
                'minHeight': '280px'
            }, id={'type': 'tank-card', 'index': subject})

        liquid_tanks.append(tank_card)

    return dbc.Row(liquid_tanks, className="g-3")