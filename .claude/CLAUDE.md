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

# output.json に NotebookLM の出力を貼り付けた後に実行
python main.py
```

## アーキテクチャ

```
NotebookLM (prompts/notebooklm.md + 論文 PDF)
  → output.json に JSON を貼り付け
  → python main.py
      → output.json を読み込み・バリデーション
      → Notion DB に新規エントリ作成（Title, Status, Tasks, Method, Data, Year, Venue）
      → Notion ページ本文に論文整理を書き込み
      → output.json を results/{タイムスタンプ}.json に移動
```

主要ファイル：
- `main.py` — エントリーポイント。output.json の読み込みから Notion 書き込みまでを統括
- `notion_helper.py` — Notion API ラッパー
- `prompts/notebooklm.md` — NotebookLM に投げるプロンプト（JSON フォーマットを指定）
- `.claude/spec.md` — 詳細仕様書（Notion スキーマ・ページブロック構成・エラー処理の定義）

## git 管理外ファイル

- `output.json` — NotebookLM からの出力を貼り付けるファイル
- `results/` — 処理済み JSON のバックアップ
- `.env` — API キー（`NOTION_API_KEY`, `NOTION_DATABASE_ID`）
- `.venv/`, `tmp/`

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
