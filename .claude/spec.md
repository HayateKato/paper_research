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
| heading_2 | 本研究の目的 |
| bulleted_list_item | 課題：{page.purpose.issue} |
| bulleted_list_item | 目標：{page.purpose.goal} |
| heading_2 | 本研究の提案手法 |
| paragraph | 処理フロー：{page.method.framework} |
| paragraph | 使用モデル： |
| bulleted_list_item × N | {page.method.models[n].model}（{page.method.models[n].purpose}）← N 件展開 |
| paragraph | 入力データ： |
| bulleted_list_item | グラフ構造：ノード：{page.method.input.graph.node} / エッジ：{page.method.input.graph.edge} |
| bulleted_list_item | その他：{page.method.input.others}（null の場合はこの行を省略） |
| paragraph | 出力：{page.method.output} |
| heading_2 | 実験 |
| paragraph | データセット： |
| bulleted_list_item × N | 名称：{name} / ドメイン：{domain} / 規模：{scale} ← N 件展開 |
| bulleted_list_item | 予測タスク：{page.experiment.task} |
| bulleted_list_item | 立証されたこと：{page.experiment.findings} |
| heading_2 | 私の研究での応用可能性 |
| bulleted_list_item | 前提条件：J-PLAT-PATの審査官引用による引用関係と各特許のテキスト情報（要約・特許請求の範囲・発明の詳細な説明）を使用する |
| bulleted_list_item | 応用できる点：{page.applicability.applicable}（null の場合は「なし」） |
| bulleted_list_item | 課題・制約：{page.applicability.limitations}（null の場合は「なし」） |

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
      "goal": "解決・実現したいこと"
    },
    "method": {
      "framework": "処理フロー（入力から出力までのステップ説明）",
      "models": [
        {"model": "モデル名と構造の説明", "purpose": "役割・目的"}
      ],
      "input": {
        "graph": {
          "node": "ノードが表すもの・埋め込みの内容",
          "edge": "エッジが表すもの（なければ null）"
        },
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
