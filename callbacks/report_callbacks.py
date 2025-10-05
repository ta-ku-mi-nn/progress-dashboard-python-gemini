"""
レポート作成機能に関連するコールバックを定義します。
"""
from dash import Input, Output, State, no_update

# データベース操作用のヘルパー関数をインポート
from data.nested_json_processor import (
    get_student_info,
    get_student_progress,
    get_student_homework
)
# PDF生成関連の関数をインポート
from utils.dashboard_pdf import render_dashboard_to_html
from utils.pdf_export import generate_pdf_from_html, create_download_data

def register_report_callbacks(app):
    """
    レポート作成に関連するコールバックを登録します。

    Args:
        app (dash.Dash): Dashアプリケーションインスタンス。
    """

    # --- 生徒選択に応じてPDF出力ボタンを有効/無効にする ---
    @app.callback(
        Output('create-report-btn', 'disabled'),
        Input('student-dropdown', 'value')
    )
    def toggle_report_button(selected_student):
        """生徒が選択されていなければボタンを無効化する。"""
        return not selected_student

    # --- PDFレポートを生成してダウンロードを開始させる ---
    @app.callback(
        Output('download-pdf-report', 'data'),
        Input('create-report-btn', 'n_clicks'),
        [State('school-dropdown', 'value'),
         State('student-dropdown', 'value')],
        prevent_initial_call=True
    )
    def generate_report(n_clicks, school, student_name):
        if not n_clicks or not school or not student_name:
            return no_update

        # 1. データベースから必要なデータをすべて取得
        student_info = get_student_info(school, student_name)
        student_progress = get_student_progress(school, student_name)
        student_homework = get_student_homework(school, student_name)

        # 2. 取得したデータを使ってHTMLを生成
        report_html = render_dashboard_to_html(
            student_info,
            student_progress,
            student_homework,
            student_name
        )

        # 3. HTMLからPDFコンテンツを生成
        pdf_content = generate_pdf_from_html(report_html)

        # 4. ダウンロード用のデータを作成して返す
        filename = f"{student_name}_学習進捗レポート.pdf"
        return create_download_data(pdf_content, filename)