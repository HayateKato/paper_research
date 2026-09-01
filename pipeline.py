"""fetch + Notion登録（+任意でNotebookLM要約書き込み）を複数論文一括で実行するスクリプト。

使い方:
    python pipeline.py "論文タイトル1" ["論文タイトル2" ...] [--with-summary]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

from notion_helper import create_db_entry, create_page_body, update_page_status, upload_pdf
from utils import sanitize_filename

SCHOLAR_DATA_FILE = Path("scholar_data.json")
SUMMARY_DIR = Path("summary")
REQUIRED_KEYS = {"title", "page"}


def parse_args() -> argparse.Namespace:
    """CLI 引数をパースする。

    Returns:
        titles（論文タイトルのリスト）と with_summary（bool）を含む Namespace
    """
    parser = argparse.ArgumentParser(description="複数論文の一括登録パイプライン")
    parser.add_argument("titles", nargs="+", help="論文タイトル（複数指定可）")
    parser.add_argument(
        "--with-summary",
        action="store_true",
        help="NotebookLM の要約をページ本文に書き込む",
    )
    return parser.parse_args()


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


def process_title(
    client: Client,
    database_id: str,
    api_key: str,
    title: str,
    scholar: dict,
) -> str:
    """1件の論文について PDF アップロードと Notion 初期エントリ作成を行う。

    Args:
        client: Notion クライアント
        database_id: 書き込み先 DB の ID
        api_key: Notion API キー（PDF アップロード用）
        title: 論文タイトル
        scholar: scholar_data.json から取得した論文データ

    Returns:
        作成した page_id

    Raises:
        Exception: Notion DB への書き込みに失敗した場合
    """
    file_upload_id = None
    pdf_path = scholar.get("pdf_path")
    if pdf_path and Path(pdf_path).exists():
        try:
            file_upload_id = upload_pdf(api_key, pdf_path)
        except Exception as e:
            print(f"警告: PDF のアップロードに失敗しました。{e}")

    return create_db_entry(
        client, database_id, title=title, purpose="未定", classification="未定", status="処理中", scholar=scholar, file_upload_id=file_upload_id
    )


def parse_notebooklm_json(text: str) -> dict | None:
    """NotebookLM の JSON 出力をパース・バリデーションする。

    Args:
        text: summary/{タイトル}.txt の内容

    Returns:
        パース済みの辞書。パース失敗・必須キー欠落時は None。
    """
    text = text.strip()
    if text.startswith("```"):
        text = "\n".join(text.splitlines()[1:])
        text = text[: text.rfind("```")]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"エラー: JSON パースに失敗しました。{e}")
        return None
    missing = REQUIRED_KEYS - data.keys()
    if missing:
        print(f"エラー: 必須キーが欠落しています: {missing}")
        return None
    return data


def finalize_title(client: Client, page_id: str, title: str) -> bool:
    """summary/{title}.txt を読み込みページ本文を書き込み Status を更新する。

    Args:
        client: Notion クライアント
        page_id: 対象ページの ID
        title: 論文タイトル

    Returns:
        成功した場合 True、失敗した場合 False（Status は "エラー" に更新済み）
    """
    path = SUMMARY_DIR / f"{sanitize_filename(title)}.txt"

    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        print(f"エラー: {path} が空です。")
        _mark_error(client, page_id)
        return False

    data = parse_notebooklm_json(path.read_text(encoding="utf-8"))
    if data is None:
        _mark_error(client, page_id)
        return False

    try:
        create_page_body(client, page_id, data)
    except Exception as e:
        print(f"警告: ページ本文の書き込みに失敗しました。{e}")
        _mark_error(client, page_id)
        return False

    try:
        update_page_status(client, page_id, "完了")
    except Exception as e:
        print(f"警告: Status の更新に失敗しました。{e}")

    return True


def _mark_error(client: Client, page_id: str) -> None:
    """ページの Status を "エラー" に更新する（失敗しても無視する）。"""
    try:
        update_page_status(client, page_id, "エラー")
    except Exception:
        pass


def main() -> None:
    """メイン処理。複数論文を一括で fetch・Notion 登録する。

    1件のタイトルの失敗が他のタイトルの処理を止めない。
    """
    load_dotenv()
    args = parse_args()

    api_key = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not api_key or not database_id:
        print("エラー: NOTION_API_KEY または NOTION_DATABASE_ID が設定されていません。")
        sys.exit(1)

    print(f"[1/2] Semantic Scholar から {len(args.titles)} 件のタイトルを取得中...")
    fetch_result = subprocess.run([sys.executable, "fetch.py", *args.titles])
    if fetch_result.returncode != 0:
        # 失敗タイトルは fetch.py 側で scholar_data.json に書き込まれないため、
        # 後続の load_scholar_data(title) is None チェックで個別にスキップされる。
        print("警告: fetch.py で一部タイトルの取得に失敗しました。scholar_data.json に存在しないタイトルはスキップします。")

    client = Client(auth=api_key)

    print("[2/2] Notion に初期エントリを作成中...")
    page_ids: dict[str, str] = {}
    failed_titles: list[str] = []

    for title in args.titles:
        scholar = load_scholar_data(title)
        if scholar is None:
            print(f"警告: {title} の scholar データが見つかりません。スキップします。")
            failed_titles.append(title)
            continue

        try:
            page_id = process_title(client, database_id, api_key, title, scholar)
        except Exception as e:
            print(f"エラー: {title} のNotion DBへの書き込みに失敗しました。{e}")
            failed_titles.append(title)
            continue

        page_ids[title] = page_id
        print(f"初期エントリを作成しました: {title} -> {page_id}")

        if not args.with_summary:
            try:
                update_page_status(client, page_id, "完了")
            except Exception as e:
                print(f"エラー: {title} の Status 更新に失敗しました。{e}")
                failed_titles.append(title)

    if args.with_summary and page_ids:
        SUMMARY_DIR.mkdir(exist_ok=True)
        summary_paths = []
        for title in page_ids:
            path = SUMMARY_DIR / f"{sanitize_filename(title)}.txt"
            if not path.exists():
                path.write_text("", encoding="utf-8")
            summary_paths.append(path)

        print()
        print("=" * 60)
        print("以下のファイルに各論文の NotebookLM JSON 出力を貼り付けてください:")
        for path in summary_paths:
            print(f"  - {path}")
        print("準備ができたら Enter を押してください。")
        print("=" * 60)
        input()

        print("\nNotion エントリを更新中...")
        for title, page_id in page_ids.items():
            if not finalize_title(client, page_id, title):
                failed_titles.append(title)

    print()
    print(f"完了: {len(page_ids)} 件成功, {len(failed_titles)} 件失敗")
    if failed_titles:
        print(f"失敗したタイトル: {failed_titles}")
        sys.exit(1)


if __name__ == "__main__":
    main()
