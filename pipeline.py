"""fetch + Notion 初期登録 + NotebookLM JSON 入力 + Notion 補完を一括実行するスクリプト。

使い方: python pipeline.py "論文タイトル"
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

from notion_helper import (
    create_initial_db_entry,
    create_page_body,
    update_db_entry_properties,
    update_page_status,
    upload_pdf,
)

SCHOLAR_DATA_FILE = Path("scholar_data.json")
PDF_FILE = Path("paper.pdf")
OUTPUT_FILE = Path("output.txt")
REQUIRED_KEYS = {"title", "tasks", "method", "data_domains", "page"}


def load_scholar_data(title: str) -> dict | None:
    if not SCHOLAR_DATA_FILE.exists():
        return None
    try:
        all_data = json.loads(SCHOLAR_DATA_FILE.read_text(encoding="utf-8"))
        return all_data.get(title)
    except (json.JSONDecodeError, OSError):
        return None


def read_json_from_file() -> str:
    if not OUTPUT_FILE.exists():
        OUTPUT_FILE.write_text("", encoding="utf-8")
    return OUTPUT_FILE.read_text(encoding="utf-8")


def parse_notebooklm_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = "\n".join(text.splitlines()[1:])
        text = text[: text.rfind("```")]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"エラー: JSON パースに失敗しました。{e}")
        sys.exit(1)
    missing = REQUIRED_KEYS - data.keys()
    if missing:
        print(f"エラー: 必須キーが欠落しています: {missing}")
        sys.exit(1)
    return data


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python pipeline.py \"論文タイトル\"")
        sys.exit(1)

    load_dotenv()
    title = sys.argv[1]

    api_key = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not api_key or not database_id:
        print("エラー: NOTION_API_KEY または NOTION_DATABASE_ID が設定されていません。")
        sys.exit(1)

    # Step 1: Semantic Scholar から取得
    print(f"[1/3] Semantic Scholar から '{title}' を取得中...")
    result = subprocess.run([sys.executable, "fetch.py", title])
    if result.returncode != 0:
        sys.exit(1)

    scholar = load_scholar_data(title)

    # Step 2: Notion に初期エントリ作成
    print("[2/3] Notion に初期エントリを作成中...")

    file_upload_id = None
    if PDF_FILE.exists():
        print(f"{PDF_FILE} を Notion にアップロード中...")
        try:
            file_upload_id = upload_pdf(api_key, str(PDF_FILE))
            if file_upload_id:
                print("PDF のアップロードが完了しました。")
        except Exception as e:
            print(f"警告: PDF のアップロードに失敗しました。{e}")

    client = Client(auth=api_key)

    try:
        page_id = create_initial_db_entry(client, database_id, title, scholar, file_upload_id)
        print(f"初期エントリを作成しました: {page_id}")
    except Exception as e:
        print(f"エラー: Notion DB への書き込みに失敗しました。{e}")
        sys.exit(1)

    # Step 3: NotebookLM JSON を入力して Notion を補完
    print()
    print("=" * 60)
    print(f"PDF を NotebookLM で解析し、JSON を {OUTPUT_FILE} に貼り付けてください。")
    print("準備ができたら Enter を押してください。")
    print("=" * 60)

    try:
        input()
    except KeyboardInterrupt:
        print("\n中断しました。")
        try:
            update_page_status(client, page_id, "エラー")
        except Exception:
            pass
        sys.exit(1)

    text = read_json_from_file()
    if not text.strip():
        print(f"エラー: {OUTPUT_FILE} が空です。")
        try:
            update_page_status(client, page_id, "エラー")
        except Exception:
            pass
        sys.exit(1)

    print("\n[3/3] Notion エントリを更新中...")

    data = parse_notebooklm_json(text)

    try:
        update_db_entry_properties(client, page_id, data)
    except Exception as e:
        print(f"エラー: プロパティの更新に失敗しました。{e}")
        try:
            update_page_status(client, page_id, "エラー")
        except Exception:
            pass
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
        sys.exit(0)

    try:
        update_page_status(client, page_id, "完了")
    except Exception as e:
        print(f"警告: Status の更新に失敗しました。{e}")

    print("完了!")


if __name__ == "__main__":
    main()
