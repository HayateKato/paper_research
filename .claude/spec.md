# 論文解析自動化パイプライン 仕様書

## 概要

NotebookLM で論文を解析した JSON 出力を `output.txt` に貼り付けて `python main.py` を実行するだけで、Notion DB エントリとページ本文を自動作成する。Claude API は使用しない。

---

## ユーザーの作業手順

1. `python fetch.py "論文タイトル"` を実行（Semantic Scholar から PDF・メタデータを取得）
2. ダウンロードされた `paper.pdf` を NotebookLM に渡し、JSON を取得
3. 返ってきた JSON を `output.txt` に貼り付けて保存
4. `python main.py` を実行

---

## 実行フロー

### fetch.py（1回目）

```
python fetch.py "論文タイトル"
  ↓
Semantic Scholar /paper/search/match でタイトル検索（1回のAPIコール）
  → レスポンスのタイトルと入力タイトルを照合してバリデーション
  → BibTeX から著者名・Venue・Year を解析
  → PDF URL 取得 → paper.pdf をダウンロード
  → scholar_data.json に { "論文タイトル": {...} } を upsert（蓄積）
```

### main.py（2回目）

```
python main.py
  ↓
output.txt を読み込んで JSON をパース・バリデーション
  ↓
scholar_data.json から output.txt の title をキーで取得（存在する場合）
  ↓
paper.pdf が存在する場合は Notion Files API でアップロード
  ↓
Notion DB に新規エントリを作成（プロパティ設定）
  ↓
Notion ページ本文に論文整理を書き込み
  ↓
output.txt を results/{タイムスタンプ}.txt に移動（二重登録防止・バックアップ）
```

---

## Notion DB スキーマ

| カラム名 | 型 | 取得元 | JSON キー / ソース |
|---|---|---|---|
| Title | title | JSON | `title` |
| Status | status | スクリプト | 完了 / エラー |
| Tasks | multi_select | JSON | `tasks` |
| Method | multi_select | JSON | `method` |
| Data | multi_select | JSON | `data_domains` |
| Year | number | JSON | `year` |
| Venue | rich_text | JSON → Semantic Scholar 補完 | `venue`（null 時は scholar_data の `venue`） |
| BibTeX | rich_text | scholar_data.json | `bibtex` |
| Authors | multi_select | scholar_data.json | `authors` |
| PDF | files | Notion Files API | paper.pdf をアップロード |

---

## Notion ページ本文

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

## 入力 JSON フォーマット（`output.txt`）

`prompts/notebooklm.md` の出力形式に準拠。

```json
{
  "title": "論文タイトル（原文）",
  "tasks": ["タスク（例: Inductive リンク予測, ノード分類）"],
  "method": ["アプローチの大分類（例: クラスタリング, RAG）"],
  "data_domains": ["データ種別（例: 特許, SNS）"],
  "year": 2024,
  "venue": "会議・ジャーナル名（不明な場合は null）",
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
    "pdf_url": "https://..."
  }
}
```

fetch.py 実行ごとにタイトルキーで upsert する。

---

## ファイル構成

```
paper_research/
├── .env                    # API キー（git 管理外）
├── .env.example
├── output.txt              # NotebookLM の出力を貼り付けるファイル（git 管理外）
├── scholar_data.json       # Semantic Scholar 取得データの蓄積（git 管理外）
├── paper.pdf               # 直近のダウンロード PDF（git 管理外）
├── results/                # 処理済みファイルのバックアップ（git 管理外）
├── main.py                 # エントリーポイント（2回目に実行）
├── fetch.py                # Semantic Scholar 取得スクリプト（1回目に実行）
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
| Semantic Scholar でヒットなし | エラーメッセージを出力して終了（scholar_data.json を更新しない） |
| Semantic Scholar API エラー | エラーメッセージを出力して終了 |
| PDF URL が存在しない（非 OA） | 警告を出力し、その他フィールドのみ scholar_data.json に保存 |
| PDF ダウンロード失敗 | 警告を出力し、pdf_url のみ scholar_data.json に保存（paper.pdf は作成しない） |

### main.py 側

| エラーケース | 対応 |
|---|---|
| `output.txt` が存在しない | エラーメッセージを出力して終了 |
| JSON パース失敗 | エラーメッセージを出力して終了（results/ に移動しない） |
| 必須キー欠落 | エラーメッセージを出力して終了（results/ に移動しない） |
| scholar_data.json が存在しない | スキップ（BibTeX 等なしで Notion 登録を続行） |
| title が scholar_data.json に未登録 | スキップ（BibTeX 等なしで Notion 登録を続行） |
| paper.pdf が存在しない | PDF カラムを空にして続行 |
| Notion Files API エラー | 警告を出力し、PDF なしで続行 |
| Notion DB 書き込みエラー | エラーメッセージを出力して終了（results/ に移動しない） |
| Notion ページ書き込みエラー | ログ出力のみ（DB エントリは作成済みのため results/ に移動する） |

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
# .env に Notion API キーを記入

# 1回目: PDF 取得
python fetch.py "論文タイトル"

# 2回目: output.txt に NotebookLM の出力を貼り付けた後に実行
python main.py
```
