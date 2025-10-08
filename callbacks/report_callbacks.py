# callbacks/report_callbacks.py

from dash import Input, Output, State, dcc
import dash_bootstrap_components as dbc
import datetime

# 必要な関数を正しくインポート
from data.nested_json_processor import get_student_info_by_id, get_student_progress_by_id
from utils.dashboard_pdf import create_dashboard_pdf


def register_report_callbacks(app):
    """PDFレポート生成に関連するコールバックを登録します。"""

    @app.callback(
        Output("download-pdf-report", "data"),
        # ↓↓↓ このコールバックは "download-report-btn" というIDのボタンで起動します
        Input("download-report-btn", "n_clicks"),
        [
            # --- ★★★ ここからが修正箇所 ★★★ ---
            # 'school-dropdown' への依存を完全に削除し、
            # 代わりにセッションに保存された生徒IDを直接参照します。
            State("student-selection-store", "data"),
            State("auth-store", "data")
            # --- ★★★ 修正箇所ここまで ★★★ ---
        ],
        prevent_initial_call=True
    )
    def generate_pdf_report(n_clicks, student_id, user_info):
        """
        選択された生徒の学習進捗レポートをPDFとして生成し、ダウンロードを開始する
        """
        if not n_clicks or not student_id or not user_info:
            return None

        # --- ★★★ ここからが修正箇所 ★★★ ---
        # 生徒IDだけを使って、必要な情報をすべて取得します。
        student_info = get_student_info_by_id(student_id)
        progress_data = get_student_progress_by_id(student_id)
        # --- ★★★ 修正箇所ここまで ★★★ ---

        if not student_info or not progress_data:
            print("PDF生成エラー: 生徒情報または進捗データが見つかりません。")
            return None
        
        # PDFをメモリ上で生成
        pdf_bytes = create_dashboard_pdf(student_info, progress_data)
        
        # ダウンロード用のファイル名を設定
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        filename = f"学習進捗レポート_{student_info.get('name', '')}_{timestamp}.pdf"
        
        # dcc.Downloadコンポーネントにデータを渡してダウンロードを実行
        return dcc.send_bytes(pdf_bytes, filename)