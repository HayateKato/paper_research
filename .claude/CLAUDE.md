# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 概要

修士研究のための論文調査・管理リポジトリ。NotebookLM で論文を解析した JSON を Notion DB に自動登録するパイプライン。

## 実行方法

```bash
# 仮想環境のセットアップ（初回のみ）
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# .env に API キーを設定（初回のみ）
cp .env.example .env

# テスト実行
pytest tests/

# 単一テストファイルの実行
pytest tests/test_main.py

# 手動フロー（2ステップ）
python fetch.py "論文タイトル"   # Semantic Scholar から取得
# → paper.pdf を NotebookLM に渡して JSON を output.txt に貼り付け
python main.py

# 一括フロー（対話型）
python pipeline.py "論文タイトル"  # fetch → Notion 初期登録 → 入力待ち → 補完
```

## アーキテクチャ

2 つのワークフローがある。

### 手動フロー

```
python fetch.py "論文タイトル"
  → Semantic Scholar からメタデータ・PDF 取得
  → scholar_data.json に保存（キャッシュ）
  → paper.pdf をダウンロード

（paper.pdf を NotebookLM で解析して JSON を output.txt に貼り付け）

python main.py
  → output.txt を読み込み・バリデーション
  → scholar_data.json からメタデータ取得
  → paper.pdf を Notion にアップロード（PDF URL がある場合のみ）
  → Notion DB に新規エントリ作成（Title, Status, Tasks, Method, Data, Year, Venue, BibTeX, Authors, PDF）
  → Notion ページ本文に論文整理を書き込み
  → output.txt を results/{タイムスタンプ}.txt にコピー
```

### 一括フロー（pipeline.py）

```
python pipeline.py "論文タイトル"
  → fetch.py を subprocess で実行（Semantic Scholar 取得）
  → Notion に初期エントリを作成（Status: 処理中）
  → output.txt への入力を待機（Enter 待ち）
  → output.txt を読み込んで Tasks/Method/Data を補完
  → ページ本文を書き込み
  → Status を "完了" に更新
```

主要ファイル：
- `main.py` — 手動フローのエントリーポイント
- `pipeline.py` — 一括フローのエントリーポイント
- `fetch.py` — Semantic Scholar から論文メタデータ・PDF を取得
- `notion_helper.py` — Notion API ラッパー（DB エントリ作成・ページ本文書き込み・PDF アップロード）
- `scholar_helper.py` — Semantic Scholar API ラッパー（検索・BibTeX 解析・PDF ダウンロード）
- `prompts/notebooklm.md` — NotebookLM に投げるプロンプト（JSON フォーマットを指定）
- `.claude/spec.md` — 詳細仕様書（Notion スキーマ・ページブロック構成・エラー処理の定義）

## git 管理外ファイル

- `output.txt` — NotebookLM からの出力を貼り付けるファイル
- `paper.pdf` — 処理対象の PDF（fetch.py でダウンロード、処理後は削除不要）
- `results/` — 処理済み output.txt のバックアップ
- `.env` — API キー（`NOTION_API_KEY`, `NOTION_DATABASE_ID`, `SEMANTIC_SCHOLAR_API_KEY`）
- `.venv/`, `tmp/`

`scholar_data.json` は git 管理内のキャッシュファイル。タイトルをキーに BibTeX・Authors・Venue・Year・PDF URL を蓄積する。

## 実装時の参照先

Notion ページのブロック構成・エラー処理の詳細は `.claude/spec.md` を参照。

## 開発プロセス

実装作業は以下の順序で進める。各フェーズ完了後に git コミットする。
**全フェーズを通じて claude-sonnet-4-6 の budget_tokens を最小（low thinking）に設定して実行する。**

1. `.claude/spec.md` を読んで仕様・実装計画を把握する
2. 各ファイルにクラス・関数定義と docstring を記述する（実装本体は空でよい）
3. `tests/` に pytest でテストコードを作成する
4. テストが全て通るように実装する
5. 各フェーズ完了後に git コミットする

### git コミットルール

コミットメッセージは `prefix: 内容` の形式とする。prefix は以下から選ぶ：

- `add` — コードやファイルの追加
- `update` — コードやファイルの修正（バグ以外）
- `fix` — バグの修正
- `remove` — コードやファイルの削除
- `refactor` — リファクタリング

コミットメッセージの内容は Claude が変更内容を踏まえて自分で考える。

Claude がコミットする場合は、コミットメッセージの末尾に `(claude)` を付ける。
例：`add: 関数定義を追加 (claude)`

## タスク・ナレッジ管理

- `.claude/todo.md` — タスク管理。作業開始時に読み、進捗を随時更新する。コンテキストリセット後もここを見れば再開できる状態に保つ。
- `.claude/knowledge.md` — ハマったことや学びを記録する。同じ問題で二度手間にならないよう、解決後すぐに追記する。

## コーディング規約

実装は以下のように docstring を必ず書く。

例：

```python
"""
足し算を行うモジュール
"""


class Adder:
    """足し算クラス

    Attributes:
        base (int): 加算の基準値
    """

    def __init__(self, base: int = 0):
        self.base = base

    def add(self, x: int, y: int) -> int:
        """2つの整数と基準値を加算する

        Args:
            x (int): 加算する整数
            y (int): 加算する整数

        Returns:
            int: x + y + base の結果

        Raises:
            TypeError: x または y が整数でない場合
        """
        return self.base + x + y
```

テストは何を確認しているのか必ず書く。

例：

```python
"""
Adderクラスのテスト。
"""

import pytest
from adder import Adder


@pytest.fixture
def adder():
    """基準値0のAdderインスタンス。"""
    return Adder(base=0)


def test_add_basic(adder):
    """add()が2つの整数の和を返すことを確認。

    add(1, 2)を呼ぶと3が返る必要がある。
    """
    assert adder.add(1, 2) == 3


def test_add_with_base():
    """baseが加算結果に含まれることを確認。

    base=10のAdderでadd(1, 2)を呼ぶと13が返る必要がある。
    """
    adder = Adder(base=10)
    assert adder.add(1, 2) == 13
```

## 報告

以下の場合は実装後に必ず報告する：

- spec.md に記載がない設計判断をした（例：エラー処理の方針、データ構造の選択）
- spec.md の仕様と異なる実装をした（例：API の呼び方、フィールド名）
- 複数の実装方法があり、どちらも仕様に反しないが一方を選んだ
