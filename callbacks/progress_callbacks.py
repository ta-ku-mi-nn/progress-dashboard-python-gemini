"""
進捗グラフの表示に関連するコールバックを定義します。
"""
from dash import Input, Output, State, html, dcc
import pandas as pd

# データ処理とグラフ生成の関数をインポート
from data.nested_json_processor import get_student_progress
# 修正後の正しい関数名をインポート
from charts.chart_generator import create_progress_bar_chart

def register_progress_callbacks(app, data):
    """
    進捗グラフの表示に関連するコールバックを登録します。

    Args:
        app (dash.Dash): Dashアプリケーションインスタンス。
        data (dict): アプリケーション起動時に読み込まれた全データ。
    """

    @app.callback(
        Output('progress-graph-container', 'children'),
        [Input('student-dropdown', 'value')],
        [State('school-dropdown', 'value')]
    )
    def update_progress_graphs(selected_student, selected_school):
        """
        生徒が選択されたら、その生徒の全科目の進捗グラフを生成して表示する。
        """
        if not selected_student or not selected_school:
            return html.Div("生徒を選択してください。", className="text-center mt-4")

        # 選択された生徒の進捗データを取得
        student_progress = get_student_progress(data, selected_school, selected_student)

        if not student_progress:
            return html.Div(f"「{selected_student}」さんの進捗データが見つかりません。",
                            className="text-center mt-4")

        # ネストした辞書データをPandas DataFrameに変換
        records = []
        for subject, levels in student_progress.items():
            for level, books in levels.items():
                for book_name, details in books.items():
                    records.append({
                        '科目': subject,
                        'ルートレベル': level,
                        '参考書名': book_name,
                        '所要時間': details.get('所要時間'),
                        '予定': details.get('予定', False),
                        '達成済': details.get('達成済', False)
                    })

        if not records:
            return html.Div("この生徒には登録されている参考書がありません。",
                            className="text-center mt-4")

        df = pd.DataFrame(records)

        # 各科目についてグラフを生成
        subjects = sorted(df['科目'].unique())
        graphs = [
            html.Div(
                dcc.Graph(
                    figure=create_progress_bar_chart(df, subject),
                    config={'displayModeBar': False}
                ),
                className="col-md-6 mb-4"
            ) for subject in subjects
        ]

        return html.Div(graphs, className="row")