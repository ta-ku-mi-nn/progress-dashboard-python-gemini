# アーカイブディレクトリ

このディレクトリには、モジュール分割前の元ファイルが保存されています。

## ファイル一覧

- `progress-dashboard-original.py`: 元の4100行モノリシックファイル
  - モジュール分割前のバックアップ
  - 機能は新しいapp.pyとモジュール群で実現されています

## 新しい構造

現在のアプリケーションは以下の構造で動作しています：

```
app.py                    # メインアプリケーション (10.00/10 Pylintスコア)
├── callbacks/            # コールバック処理
│   ├── admin_callbacks.py
│   ├── main_callbacks.py  
│   ├── progress_callbacks.py
│   └── student_callbacks.py
├── charts/               # グラフ生成
│   ├── chart_generator.py
│   └── generator.py
├── components/           # UI コンポーネント
│   └── main_layout.py
├── config/               # 設定ファイル
│   └── settings.py
├── data/                 # データ処理
│   └── processor.py
└── utils/                # ユーティリティ
    └── __init__.py
```

全てのモジュールで10.00/10のPylintスコアを達成しています。