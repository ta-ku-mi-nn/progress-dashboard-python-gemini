"""
HTML文字列からPDFを生成し、ダウンロード用のデータを作成する関数を定義します。
"""
import base64

# PDF生成には WeasyPrint ライブラリが必要です。
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

def generate_pdf_from_html(html_string):
    """
    HTML文字列からPDFデータを生成します。
    weasyprintがインストールされていない場合は、エラーメッセージを含むテキストを返します。
    """
    if WEASYPRINT_AVAILABLE:
        try:
            pdf_file = HTML(string=html_string).write_pdf()
            return pdf_file
        except Exception as e:
            error_message = f"PDF生成エラー: {e}"
            print(error_message)
            return error_message.encode('utf-8')
    else:
        message = "PDF生成機能は無効です。'weasyprint'ライブラリをインストールしてください。"
        print(f"警告: {message}")
        return message.encode('utf-8')

def create_download_data(pdf_content, filename="dashboard.pdf"):
    """
    PDFコンテンツからDashのdcc.Downloadコンポーネント用のデータを作成します。
    """
    if not pdf_content:
        return None

    encoded_pdf = base64.b64encode(pdf_content).decode('utf-8')

    # WeasyPrintが利用可能かどうかでMIMEタイプを切り替える
    content_type = "application/pdf" if WEASYPRINT_AVAILABLE else "text/plain"

    return {
        "content": encoded_pdf,
        "filename": filename,
        "base64": True,
        "type": content_type
    }