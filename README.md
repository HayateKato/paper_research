# paper_research

修士研究のための論文調査・管理リポジトリ。NotebookLM で論文を解析した JSON を Notion DB に自動登録するパイプライン。

## 概要

```
NotebookLM (prompts/notebooklm.md + 論文 PDF)
  → output.json に JSON を貼り付け
  → python main.py
      → output.json を読み込み・バリデーション
      → Notion DB に新規エントリ作成
      → Notion ページ本文に論文整理を書き込み
      → output.json を results/{タイムスタンプ}.json に移動
```

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env に Notion API キーを記入
```

### 環境変数（`.env`）

```
NOTION_API_KEY=...
NOTION_DATABASE_ID=...
```

## 使い方

1. `prompts/notebooklm.md` のプロンプトと論文 PDF を NotebookLM に投げる
2. 返ってきた JSON を `output.json` に貼り付けて保存
3. 実行する

```bash
python main.py
```

## Notion DB スキーマ

| カラム | 型 | 内容 |
|---|---|---|
| Title | title | 論文タイトル |
| Status | select | Done / Error |
| Tasks | multi_select | タスク種別 |
| Method | multi_select | 手法の大分類 |
| Data | multi_select | データ種別 |
| Year | number | 発表年 |
| Venue | rich_text | 会議・ジャーナル名 |

## ファイル構成

```
paper_research/
├── .env                    # API キー（git 管理外）
├── .env.example
├── output.json             # NotebookLM の出力を貼り付けるファイル（git 管理外）
├── results/                # 処理済み JSON のバックアップ（git 管理外）
├── main.py                 # エントリーポイント
├── notion_helper.py        # Notion API ラッパー
├── tests/                  # pytest テスト
├── prompts/
│   └── notebooklm.md       # NotebookLM に投げるプロンプト
└── requirements.txt
```
