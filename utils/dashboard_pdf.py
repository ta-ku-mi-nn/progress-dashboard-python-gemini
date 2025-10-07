# utils/dashboard_pdf.py
from jinja2 import Template
import pandas as pd
from datetime import datetime

def render_dashboard_to_html(student_info, student_progress, student_homework, student_name):
    """
    生徒の各種データからPDFの元となるHTML文字列を生成します。
    """
    
    try:
        with open('utils/pdf_template.html', 'r', encoding='utf-8') as f:
            template_str = f.read()
    except FileNotFoundError:
        return "<h1>エラー: PDFテンプレートファイルが見つかりません。</h1>"

    template = Template(template_str)

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

    # --- ★★★ ここから修正 ★★★ ---
    main_instructors = student_info.get('main_instructors', [])
    main_instructor_str = ", ".join(main_instructors) if main_instructors else '未設定'
    
    sub_instructors = student_info.get('sub_instructors', [])
    sub_instructor_str = ", ".join(sub_instructors) if sub_instructors else 'なし'

    context = {
        "student_name": student_name,
        "main_instructor": main_instructor_str,
        "sub_instructors": sub_instructor_str, # サブ講師を追加
        "generation_date": datetime.now().strftime("%Y年%m月%d日"),
        "homework_table": homework_table_html,
        "progress_table": progress_table_html
    }
    # --- ★★★ ここまで修正 ★★★ ---

    return template.render(context)