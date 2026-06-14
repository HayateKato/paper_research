# 論文解析自動化パイプライン 仕様書

## 概要

ローカルにダウンロードした論文 PDF を `papers/` フォルダに配置し、スクリプトを実行するだけで、Claude が PDF 全文を解析して Notion DB エントリとページ本文を自動作成する。ユーザーは Notion への手動入力不要。

---

## ユーザーの作業手順

1. 論文 PDF をダウンロードし `papers/` フォルダに配置
2. `python main.py` を実行

以上。

---

## 実行フロー

```
手動実行
  ↓
papers/ フォルダ内の PDF をスキャン（未処理のみ）
  ↓
Claude に PDF を直接送信 → JSON 形式で全データを一括取得（1回のみ）
  ↓
Notion DB に新規エントリを作成（プロパティ設定）
  ↓
Notion ページ本文に論文整理を書き込み
  ↓
PDF を papers/registered/ に移動
```

---

## Notion DB スキーマ

全カラムをスクリプトが自動入力する。ユーザーの手動入力不要。

| カラム名 | 型 | 取得元 | 説明 |
|---|---|---|---|
| Title | title | Claude | 論文タイトル（原題） |
| Filename | rich_text | ファイル名 | papers/ 内の PDF ファイル名（処理済み判定に使用） |
| Status | select | スクリプト | Done / Error |
| Models | multi_select | Claude | 使用モデル・アーキテクチャ（フィルタリング用） |
| Tasks | multi_select | Claude | タスク種別（フィルタリング用） |
| Data | multi_select | Claude | データドメイン（フィルタリング用） |
| Year | number | Claude | 発表年 |
| Venue | rich_text | Claude | ジャーナル・会議名（不明な場合は空） |

---

## Notion ページ本文

`prompt.md` のフォーマットに従い、以下の構成で書き込む。

```
### 本研究の目的

- 課題：どんな問題があるのか
- 目標：何を解決・実現したいのか

### 本研究の提案手法

- 使用モデル：ベースとなるモデルやアーキテクチャ
- 入力データ
    - グラフ構造：ノード・エッジの定義
    - ノード特徴量：テキスト・メタ情報など
    - その他：あれば
- 出力：何を出力するのか・形式

### 実験

- データセット
    - 名称：データセット名
    - ドメイン：論文ネットワーク・SNS・知識グラフなど
    - 規模：ノード数・エッジ数
- 予測タスク：何を予測しているのか
- 立証されたこと：何が示されたのか

### 私の研究での応用可能性

- 前提条件：JPATの審査官引用による引用関係と各特許のテキスト情報（要約・特許請求の範囲・発明の詳細な説明）を使用する
- 応用できる点：あれば
- 課題・制約：あれば
```

「前提条件」はプロンプトに含めて Claude に渡し、それをもとに「応用できる点」「課題・制約」を生成させる。ページ本文には前提条件の文章も固定テキストとして表示する。

---

## 処理済み判定

- `papers/` にある PDF のみ処理対象とする
- 処理完了後に `papers/registered/` へ移動するため、次回実行時は自動的にスキップされる
- Notion DB の Filename カラムも補助的にチェックし、移動失敗等による二重登録を防ぐ

---

## Claude プロンプト仕様

Claude の呼び出しは論文1本につき1回。PDF ファイルをそのまま API に渡し、DB プロパティ用データとページ本文用データを1つの JSON で取得する。

```python
with open("papers/foo.pdf", "rb") as f:
    pdf_data = base64.b64encode(f.read()).decode("utf-8")

client.messages.create(
    messages=[{
        "role": "user",
        "content": [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_data}},
            {"type": "text", "text": prompt}
        ]
    }]
)
```

### システムプロンプト（`prompts/system.md`）

```
あなたは機械学習・グラフ学習分野の論文を解析するアシスタントです。
添付された論文 PDF から以下の情報を JSON 形式で抽出してください。
```

### ユーザープロンプト（`prompts/analyze.md`）

```
添付の論文を解析し、JSON 形式で回答してください。

## 私の研究の前提条件
JPATの審査官引用による引用関係と各特許のテキスト情報（要約・特許請求の範囲・発明の詳細な説明）を使用する。

## 出力形式
{
  "title": "論文のタイトル（原文のまま）",
  "models": ["使用されているモデル・アーキテクチャ名（例: GCN, LSTM）"],
  "tasks": ["解いているタスク（例: リンク予測, ノード分類）"],
  "data_domains": ["使用データのドメイン（例: SNS, 論文ネットワーク）"],
  "year": 発表年（数値、不明な場合は null）,
  "venue": "掲載ジャーナルまたは会議名（不明な場合は null）",
  "page": {
    "purpose": {
      "issue": "どんな問題があるのか",
      "goal": "何を解決・実現したいのか"
    },
    "method": {
      "models": "ベースとなるモデルやアーキテクチャの詳細説明",
      "input": {
        "graph": "ノード・エッジの定義",
        "node_features": "テキスト・メタ情報など",
        "others": "あれば、なければ null"
      },
      "output": "何を出力するのか・形式"
    },
    "experiment": {
      "datasets": [{"name": "データセット名", "domain": "ドメイン", "scale": "ノード数・エッジ数"}],
      "task": "何を予測しているのか",
      "findings": "何が示されたのか"
    },
    "applicability": {
      "applicable": "上記の前提条件をもとに応用できる点（なければ null）",
      "limitations": "上記の前提条件をもとに考えられる課題・制約（なければ null）"
    }
  }
}

各配列は該当しない場合は空配列 [] としてください。
JSON のみを返してください。
```

---

## ファイル構成

```
paper_research/
├── .env                    # API キー（git 管理外）
├── .env.example            # 環境変数のサンプル
├── main.py                 # エントリーポイント
├── papers/                 # ダウンロードした PDF を配置するフォルダ（未処理）
│   └── registered/         # 処理済み PDF の移動先
├── prompts/
│   ├── system.md           # Claude システムプロンプト
│   └── analyze.md          # Claude ユーザープロンプトテンプレート
├── src/
│   ├── notion_helper.py    # Notion API ラッパー
│   └── claude_helper.py    # Claude API ラッパー（PDF を直接送信）
└── requirements.txt
```

---

## 環境変数（`.env`）

```
NOTION_API_KEY=...
NOTION_DATABASE_ID=...
ANTHROPIC_API_KEY=...
```

---

## 依存ライブラリ（`requirements.txt`）

```
anthropic
notion-client
python-dotenv
```

---

## エラーハンドリング

| エラーケース | 対応 |
|---|---|
| Claude API エラー | 1 回リトライ後も失敗なら Status=Error で Notion に登録 |
| Claude の JSON パース失敗 | Status=Error で Notion に登録 |
| Notion 書き込みエラー | ログ出力のみ（PDF は移動しない）|
| papers/registered/ への移動失敗 | ログ出力のみ（次回実行時に Notion チェックでスキップ）|

---

## 実行方法

```bash
# 環境構築
pip install -r requirements.txt
cp .env.example .env
# .env に各 API キーを記入

# PDF を papers/ フォルダに配置後に実行
python main.py
```

---

## 将来的な拡張候補（スコープ外）

- スキャン PDF への OCR 対応
- キーワードの自由タグ追加
- papers/ フォルダ監視による自動トリガー
