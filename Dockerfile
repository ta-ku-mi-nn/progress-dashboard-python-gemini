# 公式のPythonランタイムを親イメージとして使用
FROM python:3.11-slim

# コンテナ内の作業ディレクトリを設定
WORKDIR /app

# ヘッドレスChromeおよびweasyprintに必要なシステム依存関係をインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    pkg-config \
    # Google Chromeを追加
    wget \
    gnupg \
    # weasyprintの依存関係
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# requirements.txtファイルをコンテナにコピー
COPY requirements.txt .

# requirements.txtで指定されたパッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションの残りのコードをコンテナにコピー
COPY . .

# ポート8051を外部に公開
EXPOSE 8051

# 環境変数を定義
ENV NAME World

# コンテナ起動時にapp_main.pyを実行
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8051", "app_main:server"]