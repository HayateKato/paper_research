"""エントリーポイント。output.txt の読み込みから Notion 書き込みまでを統括する。"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

from notion_helper import create_db_entry, create_page_body

OUTPUT_FILE = Path("output.txt")
RESULTS_DIR = Path("results")

REQUIRED_KEYS = {"title", "tasks", "method", "data_domains", "year", "venue", "page"}


def load_output() -> dict:
    """output.txt を読み込んでパース・バリデーションする。

    Returns:
        パース済みの辞書

    Raises:
        SystemExit: ファイルなし・パース失敗・必須キー欠落時
    """
    if not OUTPUT_FILE.exists():
        print("エラー: output.txt が見つかりません。")
        sys.exit(1)

    try:
        text = OUTPUT_FILE.read_text(encoding="utf-8").strip()
        if text.startswith("```"):
            text = "\n".join(text.splitlines()[1:])
            text = text[:text.rfind("```")]
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"エラー: JSON パースに失敗しました。{e}")
        sys.exit(1)

    missing = REQUIRED_KEYS - data.keys()
    if missing:
        print(f"エラー: 必須キーが欠落しています: {missing}")
        sys.exit(1)

    return data


def archive_output() -> None:
    """output.txt を results/{タイムスタンプ}.json にコピーする。"""
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = RESULTS_DIR / f"{timestamp}.txt"
    shutil.copy2(str(OUTPUT_FILE), str(dest))
    print(f"output.txt を {dest} にコピーしました。")


def main() -> None:
    """メイン処理。"""
    load_dotenv()

    api_key = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not api_key or not database_id:
        print("エラー: NOTION_API_KEY または NOTION_DATABASE_ID が設定されていません。")
        sys.exit(1)

    data = load_output()
    client = Client(auth=api_key)

    try:
        page_id = create_db_entry(client, database_id, data)
        print(f"DB エントリを作成しました: {page_id}")
    except Exception as e:
        print(f"エラー: Notion DB への書き込みに失敗しました。{e}")
        sys.exit(1)

    try:
        create_page_body(client, page_id, data)
        print("ページ本文を書き込みました。")
    except Exception as e:
        print(f"警告: ページ本文の書き込みに失敗しました。{e}")

    archive_output()


if __name__ == "__main__":
    main()
