# progress-dashboard-python

## 概要
学習塾や教育現場向けの「学習進捗ダッシュボード」アプリケーションです。生徒・参考書・進捗・校舎・ユーザー情報を一元管理し、グラフや統計で学習状況を可視化します。Python（Dash, pandas, Plotly）で構築され、クラウド・ローカル両対応です。

## 主な特徴・できること
-- **生徒管理**
    - 生徒の追加・編集・削除
    - 生徒ごとの属性（学年・偏差値・メモ等）管理
    - 偏差値の登録・編集・グラフ化（時系列推移や分布の可視化）
- **参考書・教材管理**
    - 参考書の登録・編集・削除
    - 生徒ごとに参考書の割当・進捗記録
- **進捗記録・可視化**
    - 日付・単元ごとの進捗入力
    - 進捗グラフ（棒グラフ・折れ線・円グラフ等）自動生成
    - 校舎・学年・生徒単位での進捗集計
- **ユーザー・権限管理**
    - 管理者/一般ユーザーの権限分離
    - ログイン・ログアウト・セッション管理
- **データ入出力**
    - JSON/CSV形式でのデータエクスポート・インポート
    - データのバックアップ・リストア
- **PDFレポート出力**
    - 生徒ごとの進捗レポートをPDFで出力
- **UI/操作性**
    - シンプルなWeb UI（PC/タブレット対応）
    - モーダル・ダイアログによる直感的な操作
- **クラウド運用**
    - Oracle Cloud, Google Cloud, AWS, さくらVPS等で運用実績
    - ファイアウォール・SSH・SCP/WinSCP対応

## こんな用途におすすめ
- 学習塾の生徒進捗・教材管理
- 校舎ごとの学習状況の一元把握
- 生徒の偏差値推移や分布の可視化・分析
- 家庭教師・個別指導の進捗記録
- 小規模スクールの教材・生徒台帳
- 教育現場のデータ可視化・保護者向けレポート

## セットアップ手順
1. サーバーにSSH接続
2. 必要パッケージのインストール
        ```sh
        sudo apt update
        sudo apt install python3 python3-pip git
        ```
3. プロジェクトをアップロード（例: scpやWinSCP）
4. 依存パッケージのインストール
        ```sh
        cd progress-dashboard-python
        pip3 install -r requirements.txt
        ```
5. アプリ起動
        ```sh
        python3 app_with_auth_json.py
        ```
6. ブラウザで `http://<サーバーIP>:8050` にアクセス

## ディレクトリ構成
```
progress-dashboard-python/
├── app_with_auth_json.py         # Dashアプリ本体
├── data/                        # データ管理モジュール
├── components/                  # UI部品
├── callbacks/                   # Dashコールバック
├── charts/                      # グラフ生成
├── auth/                        # 認証・ユーザー管理
├── tests/                       # テスト
├── route-subject-text-time.json # 進捗データ
└── README.md                    # このファイル
```

## よくある質問
- Q. クラウドで編集や運用はできる？
     - A. SSH/WinSCP/VSCode Remote-SSHで編集・運用可能です。
- Q. 無料で運用できる？
     - A. Oracle Cloud Free TierやGCP無料枠で小規模運用が可能です。
- Q. Windows/Macでも動く？
     - A. Python3が動作すればローカルPCでも利用できます。
- Q. データの初期化やバックアップは？
     - A. JSON/CSVエクスポートやファイルバックアップで対応可能です。
- Q. PDF出力ができない場合は？
     - A. `wkhtmltopdf`のインストールを確認してください。

## ライセンス
MIT License
