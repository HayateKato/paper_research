# paper_research

修士研究のための論文調査・管理リポジトリ。Semantic Scholar から論文メタデータ・PDFを取得し、Notion DBに自動登録するパイプライン。NotebookLMで解析したJSONをページ本文に書き込む機能もオプションで利用できる。

## 概要

```
python pipeline.py "論文タイトル1" ["論文タイトル2" ...] [--with-summary]
  → fetch.py で Semantic Scholar からメタデータ・PDF・DOI を取得
  → Notion DB に新規エントリを作成（Status: 処理中 → 完了）
  → --with-summary 指定時のみ、summary/ に貼り付けた NotebookLM JSON をページ本文へ書き込み
```

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env に Notion / Semantic Scholar API キーを記入
```

### 環境変数（`.env`）

```
NOTION_API_KEY=...
NOTION_DATABASE_ID=...
SEMANTIC_SCHOLAR_API_KEY=...
```

## 使い方

### メタデータのみ一括登録

```bash
python pipeline.py "論文タイトル1" "論文タイトル2"
```

### NotebookLM要約も書き込む場合

```bash
python pipeline.py "論文タイトル1" "論文タイトル2" --with-summary
```

1. `prompts/notebooklm.md` のプロンプトと各論文の PDF（`pdfs/` 配下）を NotebookLM に投げる
2. 返ってきた JSON を対応する `summary/{タイトル}.txt` に貼り付ける
3. 全ファイルへの入力が終わったら Enter を押す

## Notion DB スキーマ

| カラム | 型 | 内容 |
|---|---|---|
| Title | title | 論文タイトル |
| Status | status | 処理中 / 完了 / エラー |
| purpose | multi_select | 常に空欄（手動タグ付け） |
| Data | multi_select | 常に空欄（手動タグ付け） |
| github | url | 常に空欄（手動入力） |
| DOI | url | Semantic Scholar から取得 |
| Authors | multi_select | 著者名 |
| Year | number | 発表年 |
| Venue | rich_text | 会議・ジャーナル名 |
| BibTeX | rich_text | BibTeX 文字列 |
| PDF | files | ダウンロードした PDF |

## ファイル構成

```
paper_research/
├── .env                    # API キー（git 管理外）
├── .env.example
├── scholar_data.json       # Semantic Scholar 取得データの蓄積
├── pdfs/                   # ダウンロードした PDF（git 管理外）
├── summary/                # --with-summary 指定時の NotebookLM JSON 貼り付け先（git 管理外）
├── pipeline.py             # エントリーポイント
├── utils.py                # 共通ユーティリティ（ファイル名サニタイズ等）
├── fetch.py                # Semantic Scholar 取得スクリプト
├── notion_helper.py        # Notion API ラッパー
├── scholar_helper.py       # Semantic Scholar API ラッパー
├── tests/                  # pytest テスト
├── prompts/
│   └── notebooklm.md       # NotebookLM に投げるプロンプト
└── requirements.txt
```
