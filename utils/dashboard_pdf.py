from jinja2 import Template
import pandas as pd
import datetime

def render_dashboard_to_html(student_progress_data, student_info, student_name):
    """
    生徒の進捗データと個人情報から、PDFの元となるHTML文字列を生成します。

    Args:
        student_progress_data (dict): 生徒の'progress'オブジェクト。
        student_info (dict): 生徒の'data'オブジェクト（講師名など）。
        student_name (str): 生徒の名前。
    """
    
    # HTMLテンプレートファイルを読み込む
    try:
        with open('utils/pdf_template.html', 'r', encoding='utf-8') as f:
            template_str = f.read()
    except FileNotFoundError:
        return "<h1>エラー: PDFテンプレートファイルが見つかりません。</h1>"

    template = Template(template_str)
    
    # データを整形
    records = []
    for subject, levels in student_progress_data.items():
        for level, books in levels.items():
            for book_name, details in books.items():
                # 「予定」または「達成済」がTrueの参考書のみをPDFに記載
                if details.get('予定') or details.get('達成済'):
                    records.append({
                        '科目': subject,
                        'ルートレベル': level,
                        '参考書名': book_name,
                        'ステータス': '達成' if details.get('達成済') else '予定'
                    })
    
    df = pd.DataFrame(records)
    
    # テンプレートに渡すためのデータコンテキストを作成
    context = {
        "student_name": student_name,
        "main_instructor": student_info.get('メイン講師', '未設定'),
        "generation_date": datetime.datetime.now().strftime("%Y年%m月%d日"),
        "progress_table": df.to_html(index=False, classes='table table-striped table-sm') if not df.empty else "<p>表示対象の学習計画がありません。</p>"
    }

    return template.render(context)