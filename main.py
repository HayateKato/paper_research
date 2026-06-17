"""エントリーポイント。output.txt の読み込みから Notion 書き込みまでを統括する。"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

from notion_helper import create_db_entry, create_page_body, update_page_status, upload_pdf

OUTPUT_FILE = Path("output.txt")
RESULTS_DIR = Path("results")
SCHOLAR_DATA_FILE = Path("scholar_data.json")
PDF_FILE = Path("paper.pdf")

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


def load_scholar_data(title: str) -> dict | None:
    """scholar_data.json から title に対応するデータを読み込む。

    Args:
        title: 検索するキー（論文タイトル）

    Returns:
        scholar データの辞書。ファイルがない・タイトルが未登録の場合は None。
    """
    if not SCHOLAR_DATA_FILE.exists():
        return None
    try:
        all_data = json.loads(SCHOLAR_DATA_FILE.read_text(encoding="utf-8"))
        return all_data.get(title)
    except (json.JSONDecodeError, OSError):
        return None


def archive_output() -> None:
    """output.txt を results/{タイムスタンプ}.txt にコピーする。"""
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
    scholar = load_scholar_data(data["title"])
    if scholar:
        print(f"scholar_data.json からデータを読み込みました: {data['title']}")
    else:
        print("scholar_data.json が見つからないか、タイトルが未登録です。BibTeX 等はスキップします。")

    file_upload_id = None
    if PDF_FILE.exists():
        print(f"{PDF_FILE} を Notion にアップロード中...")
        try:
            file_upload_id = upload_pdf(api_key, str(PDF_FILE))
            if file_upload_id:
                print("PDF のアップロードが完了しました。")
            else:
                print("警告: PDF アップロードに失敗しました（ファイルなし）。")
        except Exception as e:
            print(f"警告: PDF のアップロードに失敗しました。{e}")

    client = Client(auth=api_key)

    try:
        page_id = create_db_entry(client, database_id, data, scholar=scholar, file_upload_id=file_upload_id)
        print(f"DB エントリを作成しました: {page_id}")
    except Exception as e:
        print(f"エラー: Notion DB への書き込みに失敗しました。{e}")
        sys.exit(1)

    try:
        create_page_body(client, page_id, data)
        print("ページ本文を書き込みました。")
    except Exception as e:
        print(f"警告: ページ本文の書き込みに失敗しました。{e}")
        try:
            update_page_status(client, page_id, "エラー")
        except Exception:
            pass

    archive_output()


if __name__ == "__main__":
    main()
