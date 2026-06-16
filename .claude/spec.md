# 論文解析自動化パイプライン 仕様書

## 概要

NotebookLM で論文を解析した JSON 出力を `output.json` に貼り付けて `python main.py` を実行するだけで、Notion DB エントリとページ本文を自動作成する。Claude API は使用しない。

---

## ユーザーの作業手順

1. NotebookLM に `prompts/user.md`（プロンプト）と論文 PDF を投げる
2. 返ってきた JSON を `output.json` に貼り付けて保存
3. `python main.py` を実行

以上。

---

## 実行フロー

```
python main.py
  ↓
output.json を読み込んで JSON をパース・バリデーション
  ↓
Notion DB に新規エントリを作成（プロパティ設定）
  ↓
Notion ページ本文に論文整理を書き込み
  ↓
output.json を results/{タイムスタンプ}.json に移動（二重登録防止・バックアップ）
```

---

## Notion DB スキーマ

| カラム名 | 型 | 取得元 | JSON キー |
|---|---|---|---|
| Title | title | JSON | `title` |
| Status | select | スクリプト | Done / Error |
| Tasks | multi_select | JSON | `tasks` |
| Method | multi_select | JSON | `method` |
| Data | multi_select | JSON | `data_domains` |
| Year | number | JSON | `year` |
| Venue | rich_text | JSON | `venue` |

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

---

## 入力 JSON フォーマット（`output.json`）

`prompt/notebooklm.md` の出力形式に準拠。

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
    }
  }
}
```

---

## ファイル構成

```
paper_research/
├── .env                    # API キー（git 管理外）
├── .env.example
├── output.json             # NotebookLM の出力を貼り付けるファイル（git 管理外）
├── results/                # 処理済み JSON のバックアップ（git 管理外）
├── main.py                 # エントリーポイント
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
```

---

## エラーハンドリング

| エラーケース | 対応 |
|---|---|
| `output.json` が存在しない | エラーメッセージを出力して終了 |
| JSON パース失敗 | エラーメッセージを出力して終了（results/ に移動しない） |
| 必須キー欠落 | エラーメッセージを出力して終了（results/ に移動しない） |
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

# output.json に NotebookLM の出力を貼り付けた後に実行
python main.py
```
