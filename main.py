"""エントリーポイント。output.json の読み込みから Notion 書き込みまでを統括する。"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

from notion_helper import create_db_entry, create_page_body

OUTPUT_FILE = Path("output.json")
RESULTS_DIR = Path("results")

REQUIRED_KEYS = {"title", "tasks", "method", "data_domains", "year", "venue", "page"}


def load_output() -> dict:
    """output.json を読み込んでパース・バリデーションする。

    Returns:
        パース済みの辞書

    Raises:
        SystemExit: ファイルなし・パース失敗・必須キー欠落時
    """
    pass


def archive_output() -> None:
    """output.json を results/{タイムスタンプ}.json に移動する。"""
    pass


def main() -> None:
    """メイン処理。"""
    pass


if __name__ == "__main__":
    main()
