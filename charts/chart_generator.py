"""
グラフ生成関数
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def create_progress_bar_chart(df, subject):
    """
    指定された科目の進捗データ（DataFrame）から、ルートレベル別の達成率を示す棒グラフを生成します。

    Args:
        df (pd.DataFrame): '科目', 'ルートレベル', '参考書名', '達成済' を含むDataFrame。
        subject (str): グラフを生成する対象の科目名。

    Returns:
        go.Figure: Plotlyグラフオブジェクト。
    """
    # 対象科目のデータが存在しない場合の処理
    if df.empty or subject not in df['科目'].unique():
        fig = go.Figure()
        fig.update_layout(
            title_text=f"{subject}: 表示できるデータがありません",
            xaxis={'visible': False},
            yaxis={'visible': False},
            annotations=[{
                "text": "データなし",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 16}
            }],
            margin=dict(t=50, b=10, l=10, r=10),
            height=300
        )
        return fig

    # 対象科目のデータを抽出し、達成状況を数値化（True -> 1, False -> 0）
    subject_df = df[df['科目'] == subject].copy()
    subject_df['達成済'] = subject_df['達成済'].apply(lambda x: 1 if x else 0)

    # ルートレベルごとに参考書の総数と達成数を集計
    progress_by_level = subject_df.groupby('ルートレベル').agg(
        総数=('参考書名', 'count'),
        達成数=('達成済', 'sum')
    ).reset_index()

    # 達成率を計算（0除算を避けるため .fillna(0) を使用）
    progress_by_level['達成率'] = \
        (progress_by_level['達成数'] / progress_by_level['総数'] * 100).fillna(0)

    # 棒グラフを生成
    fig = px.bar(
        progress_by_level,
        x='ルートレベル',
        y='達成率',
        title=f'{subject}のルートレベル別達成率',
        labels={'達成率': '達成率 (%)', 'ルートレベル': 'ルートレベル'},
        text=progress_by_level['達成率'].apply(lambda x: f'{x:.1f}%')
    )

    # グラフの見た目を調整
    fig.update_traces(textposition='outside')
    fig.update_yaxes(range=[0, 110])
    fig.update_layout(
        margin=dict(t=50, b=10, l=10, r=10),
        height=300
    )
    return fig