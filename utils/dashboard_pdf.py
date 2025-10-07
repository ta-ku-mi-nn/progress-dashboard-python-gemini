"""
データベースから取得したデータに基づき、
PDFレポートの元となるHTMLを生成する関数を定義します。
"""
from jinja2 import Template
import pandas as pd
from datetime import datetime

def render_dashboard_to_html(student_info, student_progress, student_homework, student_name):
    """
    生徒の各種データからPDFの元となるHTML文字列を生成します。

    Args:
        student_info (dict): 生徒の個人情報（講師名など）。
        student_progress (dict): 生徒の参考書進捗データ。
        student_homework (list): 生徒の宿題リスト。
        student_name (str): 生徒の名前。
    """
    
    # HTMLテンプレートファイルを読み込む
    try:
        with open('utils/pdf_template.html', 'r', encoding='utf-8') as f:
            template_str = f.read()
    except FileNotFoundError:
        return "<h1>エラー: PDFテンプレートファイルが見つかりません。</h1>"

    template = Template(template_str)

    # --- 宿題データをHTMLテーブルに変換 ---
    if student_homework:
        homework_df = pd.DataFrame(student_homework)
        # 不要な 'id' と 'student_id' 列を削除し、表示する列の順番を定義
        homework_df = homework_df[['subject', 'task', 'due_date', 'status']]
        homework_df.columns = ['科目', '課題内容', '提出期限', 'ステータス'] # 列名を日本語に
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

    # テンプレートに渡すためのデータコンテキストを作成
    context = {
        "student_name": student_name,
        # ★★★ 修正: 'メイン講師' -> 'main_instructor' ★★★
        "main_instructor": student_info.get('main_instructor', '未設定'),
        "generation_date": datetime.now().strftime("%Y年%m月%d日"),
        "homework_table": homework_table_html,
        "progress_table": progress_table_html
    }

    return template.render(context)