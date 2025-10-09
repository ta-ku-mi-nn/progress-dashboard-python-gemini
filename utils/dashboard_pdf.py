# utils/dashboard_pdf.py

from jinja2 import Template
import pandas as pd
from datetime import datetime
import os

# PDF変換ライブラリをインポート
try:
    import weasyprint
except ImportError:
    weasyprint = None

# --- ★★★ ここから修正 ★★★ ---
def create_dashboard_pdf(student_info, student_progress, all_subjects_chart_base64):
    """
    生徒情報、進捗データ、グラフ画像を受け取り、PDFのバイナリデータを生成して返す。
    """
    if weasyprint is None:
        print("エラー: PDF生成ライブラリ 'weasyprint' がインストールされていません。")
        print("コマンド: pip install weasyprint")
        error_html = "<h1>PDF Export Error</h1><p>Required library 'weasyprint' is not installed.</p>"
        return error_html.encode('utf-8')

    html_content = render_dashboard_to_html(
        student_info,
        student_progress,
        [], # 現状、宿題データはレポートに含めない
        student_info.get("name", "不明な生徒"),
        all_subjects_chart_base64 # グラフ画像データを渡す
    )
    # --- ★★★ ここまで修正 ★★★ ---

    # HTMLをPDFに変換
    css_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'pdf_style.css')
    
    if os.path.exists(css_path):
        css = weasyprint.CSS(css_path)
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf(stylesheets=[css])
    else:
        print(f"警告: CSSファイルが見つかりません: {css_path}")
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        
    return pdf_bytes

# --- ★★★ ここから修正 ★★★ ---
def render_dashboard_to_html(student_info, student_progress, student_homework, student_name, all_subjects_chart_base64):
    """
    生徒の各種データからPDFの元となるHTML文字列を生成します。
    """
    
    try:
        template_path = os.path.join(os.path.dirname(__file__), 'pdf_template.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            template_str = f.read()
    except FileNotFoundError:
        return "<h1>エラー: PDFテンプレートファイルが見つかりません。</h1>"

    template = Template(template_str)
    # (中略: 宿題と参考書のテーブル生成ロジックは変更なし)
# --- ★★★ ここまで修正 ★★★ ---

    # --- 宿題データをHTMLテーブルに変換 ---
    if student_homework:
        homework_df = pd.DataFrame(student_homework)
        homework_df = homework_df[['subject', 'task', 'due_date', 'status']]
        homework_df.columns = ['科目', '課題内容', '提出期限', 'ステータス']
        homework_table_html = homework_df.to_html(index=False, classes='table table-striped table-sm')
    else:
        homework_table_html = "<p>登録されている宿題はありません。</p>"
    
    # --- 参考書進捗データをHTMLテーブルに変換 ---
    progress_records = []
    for subject, levels in student_progress.items():
        for level, books in levels.items():
            for book_name, details in books.items():
                if details.get('予定') or details.get('達成済'):
                    progress_records.append({
                        '科目': subject,
                        'ルートレベル': level,
                        '参考書名': book_name,
                        'ステータス': '達成' if details.get('達成済') else '予定'
                    })
    
    if progress_records:
        progress_df = pd.DataFrame(progress_records)
        progress_table_html = progress_df.to_html(index=False, classes='table table-striped table-sm')
    else:
        progress_table_html = "<p>予定されている参考書はありません。</p>"

    main_instructors = student_info.get('main_instructors', [])
    main_instructor_str = ", ".join(main_instructors) if main_instructors else '未設定'
    
    sub_instructors = student_info.get('sub_instructors', [])
    sub_instructor_str = ", ".join(sub_instructors) if sub_instructors else 'なし'

    # --- ★★★ ここから修正 ★★★ ---
    context = {
        "student_name": student_name,
        "main_instructor": main_instructor_str,
        "sub_instructors": sub_instructor_str,
        "generation_date": datetime.now().strftime("%Y年%m月%d日"),
        "homework_table": homework_table_html,
        "progress_table": progress_table_html,
        "all_subjects_chart": all_subjects_chart_base64, # コンテキストに画像データを追加
    }
    # --- ★★★ ここまで修正 ★★★ ---

    return template.render(context)