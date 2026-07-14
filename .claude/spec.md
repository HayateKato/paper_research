# 論文解析自動化パイプライン 仕様書

## 概要

`python pipeline.py "論文タイトル" ["論文タイトル2" ...] [--with-summary]` を実行するだけで、Semantic Scholar からのメタデータ・PDF取得とNotion DBエントリ作成を自動で行う。複数タイトルを一度に指定して一括登録できる。`--with-summary` を付けた場合のみ、NotebookLMで解析したJSONをページ本文に書き込む（従来の詳細な論文整理フロー）。Claude API は使用しない。

---

## ユーザーの作業手順

### 基本（メタデータのみ登録）

```bash
python pipeline.py "論文タイトル1" "論文タイトル2" "論文タイトル3"
```

Semantic Scholar からBibTeX・著者・venue・year・DOI・PDFを取得し、Notion DBに新規エントリを作成する。ページ本文は書き込まない。

### NotebookLM要約も書き込む場合

```bash
python pipeline.py "論文タイトル1" "論文タイトル2" --with-summary
```

1. 各論文のメタデータ取得・PDF取得・Notion初期エントリ作成（Status: 処理中）を行う。
2. `summary/{サニタイズ済みタイトル}.txt` が論文ごとに用意されるので、各PDFをNotebookLMに渡し、返ってきたJSONを対応するファイルに貼り付ける。
3. 全ファイルへの入力が終わったらEnterを押す。
4. スクリプトが各 `summary/*.txt` を読み込み、ページ本文書き込みとStatus更新（完了 / エラー）を行う。

---

## 実行フロー

### pipeline.py

```
python pipeline.py "title1" ["title2" ...] [--with-summary]
  ↓
[1] fetch.py をタイトルリストまとめて subprocess 実行
  → Semantic Scholar /paper/search/match でタイトルごとに検索
  → BibTeX から著者名・Venue・Year を解析、externalIds から DOI を取得
  → PDF URL 取得 → pdfs/{サニタイズ済みタイトル}.pdf をダウンロード
  → scholar_data.json に { "論文タイトル": {...} } を upsert（蓄積）
  → 1件が失敗（ヒットなし・APIエラー等）してもスキップして残りを継続
  ↓
[2] タイトルごとに Notion 初期エントリを作成（Status: 処理中）
  → PDF が取得できていれば Notion Files API でアップロード
  → 1件の失敗が他のタイトルの処理を止めない
  ↓
[3-A] --with-summary 未指定の場合
  → 各エントリの Status を即座に "完了" に更新して終了
  ↓
[3-B] --with-summary 指定の場合
  → summary/{サニタイズ済みタイトル}.txt を論文ごとに用意
  → 全ファイルへの入力を1回だけ待機（Enter待ち）
  → 各 summary/*.txt を読み込み、ページ本文を書き込み
  → 成功したタイトルは Status を "完了"、失敗したタイトルのみ "エラー" に更新
```

---

## Notion DB スキーマ

| カラム名 | 型 | 取得元 | 備考 |
|---|---|---|---|
| Title | title | CLI引数のタイトル | |
| Status | status | スクリプト | 処理中 / 完了 / エラー |
| purpose | multi_select | なし | 常に空欄。ユーザーがNotion上で手動タグ付け |
| Data | multi_select | なし | 常に空欄。ユーザーがNotion上で手動タグ付け |
| github | url | なし | 常に空欄。ユーザーがNotion上で手動入力 |
| DOI | url | scholar_data.json の `doi` | Semantic Scholar externalIds.DOI |
| Authors | multi_select | scholar_data.json の `authors` | |
| Year | number | scholar_data.json の `year` | |
| Venue | rich_text | scholar_data.json の `venue` | |
| BibTeX | rich_text | scholar_data.json の `bibtex` | |
| PDF | files | Notion Files API | ファイル名は `{サニタイズ済みタイトル}.pdf` |

**注意:** Tasks・Method プロパティは廃止した。NotebookLM出力の `tasks`/`method`/`data_domains` はNotionのDBプロパティには一切書き込まれない（`--with-summary` 時もページ本文にのみ反映される）。

---

## Notion ページ本文（`--with-summary` 指定時のみ書き込み）

DB エントリのページ本文に、以下の Notion ブロック構成で1ページにまとめて書き込む。

| ブロック種別 | 内容 |
|---|---|
| heading_2 | 概要 |
| heading_3 | 課題 |
| paragraph | {page.purpose.issue} |
| heading_3 | 目標 |
| paragraph | {page.purpose.goal} |
| heading_3 | 新規性 |
| paragraph | {page.purpose.new} |
| heading_2 | 提案手法 |
| heading_3 | 処理フロー |
| paragraph | {page.method.framework} |
| heading_3 | 使用モデル |
| bulleted_list_item × N | {page.method.models[n].model}（{page.method.models[n].purpose}）← N 件展開 |
| heading_3 | 入力 |
| paragraph | ノード：{page.method.input.node} |
| paragraph | エッジ：{page.method.input.edge}（null の場合はこの行を省略） |
| paragraph | その他：{page.method.input.others}（null の場合はこの行を省略） |
| heading_3 | 出力 |
| paragraph | {page.method.output} |
| heading_2 | 実験 |
| heading_3 | データセット |
| table（3列：名称・ドメイン・規模） | {page.experiment.datasets} ← N 行展開 |
| heading_3 | 予測タスク |
| paragraph | {page.experiment.task} |
| heading_3 | 立証されたこと |
| paragraph | {page.experiment.findings} |
| heading_2 | 特許ネットワークへの応用可能性 |
| heading_3 | 応用できる点 |
| paragraph | {page.applicability.applicable}（null の場合は「なし」） |
| heading_3 | 課題・制約 |
| paragraph | {page.applicability.limitations}（null の場合は「なし」） |
| heading_2 | 関連研究（related_works が空でない場合のみ） |
| heading_3 × N | {page.related_works[n].title} ← N 件展開 |
| paragraph × N | {page.related_works[n].relation} |

---

## 入力 JSON フォーマット（`summary/{タイトル}.txt`、`--with-summary` 指定時のみ使用）

`prompts/notebooklm.md` の出力形式に準拠。必須キーは `title`, `page` の2つのみ（`tasks`/`method`/`data_domains` は出力されても無視する）。

```json
{
  "title": "論文タイトル（原文）",
  "tasks": ["タスク（例: Inductive リンク予測, ノード分類）"],
  "method": ["アプローチの大分類（例: クラスタリング, RAG）"],
  "data_domains": ["データ種別（例: 特許, SNS）"],
  "page": {
    "purpose": {
      "issue": "問題の説明",
      "goal": "解決・実現したいこと",
      "new": "従来手法と比較した新規性・差別化ポイント"
    },
    "method": {
      "framework": "処理フロー（入力から出力までのステップ説明）",
      "models": [
        {"model": "モデル名と構造の説明", "purpose": "役割・目的"}
      ],
      "input": {
        "node": "ノードが表すもの・埋め込みの内容",
        "edge": "エッジが表すもの・埋め込みの内容（なければ null）",
        "others": "その他の入力（なければ null）"
      },
      "output": "出力内容・形式"
    },
    "experiment": {
      "datasets": [
        {"name": "データセット名", "domain": "データ種別", "scale": "ノード数・エッジ数"}
      ],
      "task": "予測タスク",
      "findings": "立証されたこと"
    },
    "applicability": {
      "applicable": "応用できる点（なければ null）",
      "limitations": "課題・制約（なければ null）"
    },
    "related_works": [
      {"title": "関連論文タイトル（原文）", "relation": "本研究との違いや関係"}
    ]
  }
}
```

---

## scholar_data.json フォーマット（蓄積型・タイトルをキー）

```json
{
  "論文タイトル A": {
    "bibtex": "@article{...}",
    "authors": ["Author A", "Author B"],
    "venue": "ICLR 2024",
    "year": 2024,
    "doi": "10.1145/xxxxxxx",
    "pdf_url": "https://...",
    "pdf_path": "pdfs/論文タイトルA.pdf"
  }
}
```

fetch.py 実行ごとにタイトルキーで upsert する。`doi`/`pdf_path` は取得・保存できなかった場合 `null` になる。

---

## ファイル構成

```
paper_research/
├── .env                    # API キー（git 管理外）
├── .env.example
├── scholar_data.json       # Semantic Scholar 取得データの蓄積（git 管理外）
├── pdfs/                   # ダウンロードしたPDF（{タイトル}.pdf、git 管理外）
├── summary/                # --with-summary 指定時の NotebookLM JSON 貼り付け先（git 管理外）
├── results/                # （廃止予定。旧手動フローのバックアップ用ディレクトリ）
├── pipeline.py             # エントリーポイント
├── utils.py                # ファイル名サニタイズ等の共通ユーティリティ
├── fetch.py                # Semantic Scholar 取得スクリプト（pipeline.py から subprocess 実行）
├── scholar_helper.py       # Semantic Scholar API ラッパー
├── notion_helper.py        # Notion API ラッパー
├── prompts/
│   └── notebooklm.md       # NotebookLM に投げるプロンプト
└── requirements.txt
```

---

## 環境変数（`.env`）

```
NOTION_API_KEY=...
NOTION_DATABASE_ID=...
SEMANTIC_SCHOLAR_API_KEY=...
```

---

## 依存ライブラリ（`requirements.txt`）

```
notion-client
python-dotenv
requests
```

---

## エラーハンドリング

### fetch.py 側

| エラーケース | 対応 |
|---|---|
| Semantic Scholar でヒットなし | 該当タイトルのみスキップし、警告を出力して次のタイトルへ継続 |
| Semantic Scholar API エラー | 該当タイトルのみスキップし、警告を出力して次のタイトルへ継続 |
| PDF URL が存在しない（非 OA） | 警告を出力し、その他フィールドのみ scholar_data.json に保存 |
| PDF ダウンロード失敗 | 警告を出力し、pdf_url のみ scholar_data.json に保存（pdf_path は null） |
| 全タイトル中1件以上が失敗 | 失敗したタイトル一覧を表示し、プロセスは非0で終了するが、成功分は scholar_data.json に保存済み |

### pipeline.py 側

| エラーケース | 対応 |
|---|---|
| NOTION_API_KEY / NOTION_DATABASE_ID 未設定 | エラーメッセージを出力して終了 |
| fetch.py の実行で1件以上失敗 | 失敗したタイトルはNotion登録もスキップし、成功したタイトルのみ処理を継続 |
| Notion Files API エラー | 警告を出力し、PDF なしで続行 |
| Notion DB 書き込みエラー | 該当タイトルのみエラーとして記録し、残りのタイトルは処理を継続 |
| `summary/{タイトル}.txt` が存在しない・空・JSON不正（--with-summary時） | 該当タイトルのみ Status を "エラー" に更新し、残りのタイトルは処理を継続 |
| ページ本文書き込みエラー（--with-summary時） | 該当タイトルの Status を "エラー" に更新し、残りのタイトルは処理を継続 |

---

## 実行環境

- Python 3.14（システムの `python3` を使用）
- venv で仮想環境を管理する

## 実行方法

```bash
# 仮想環境の作成と有効化
python3 -m venv .venv
source .venv/bin/activate

# 依存ライブラリのインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .env に Notion / Semantic Scholar API キーを記入

# メタデータのみ一括登録
python pipeline.py "論文タイトル1" "論文タイトル2"

# NotebookLM要約も書き込む場合
python pipeline.py "論文タイトル1" "論文タイトル2" --with-summary
```
