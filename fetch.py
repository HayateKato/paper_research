"""Semantic Scholar から論文メタデータと PDF を取得するスクリプト。

使い方: python fetch.py "論文タイトル1" ["論文タイトル2" ...]
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from scholar_helper import ScholarHelper
from utils import sanitize_filename

SCHOLAR_DATA_FILE = Path("scholar_data.json")
PDF_DIR = Path("pdfs")


def load_scholar_data() -> dict:
    """scholar_data.json を読み込む。ファイルがない・空の場合は空辞書を返す。

    Returns:
        タイトルをキーとした論文データの辞書
    """
    if SCHOLAR_DATA_FILE.exists():
        text = SCHOLAR_DATA_FILE.read_text(encoding="utf-8").strip()
        if not text:
            return {}
        return json.loads(text)
    return {}


def save_scholar_data(data: dict) -> None:
    """scholar_data.json に data を保存する。

    Args:
        data: タイトルをキーとした論文データの辞書
    """
    SCHOLAR_DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fetch_one(title: str, api_key: str | None, scholar_data: dict) -> dict | None:
    """1件の論文タイトルについて Semantic Scholar から取得し scholar_data を更新する。

    キャッシュ済みの場合はAPI呼び出しをスキップし、PDFが未取得なら再ダウンロードのみ行う。

    Args:
        title: 論文タイトル
        api_key: Semantic Scholar API キー
        scholar_data: 更新対象の scholar_data 辞書（インプレースで更新する）

    Returns:
        取得した論文データの辞書（bibtex/authors/venue/year/doi/pdf_url/pdf_path）。
        取得に失敗した場合は None（scholar_data は変更しない）。
    """
    helper = ScholarHelper(api_key=api_key)
    pdf_path = PDF_DIR / f"{sanitize_filename(title)}.pdf"

    if title in scholar_data:
        print(f"キャッシュ済み: {title}（API スキップ）")
        cached = scholar_data[title]
        pdf_url = cached.get("pdf_url")
        if pdf_url and not pdf_path.exists():
            print(f"PDF を再ダウンロード中: {pdf_url}")
            PDF_DIR.mkdir(exist_ok=True)
            success = helper.download_pdf(pdf_url, dest=str(pdf_path))
            if success:
                print(f"PDF を {pdf_path} に保存しました。")
                cached["pdf_path"] = str(pdf_path)
            else:
                print("警告: PDF のダウンロードに失敗しました。")
        return cached

    print(f"Semantic Scholar で検索中: {title}")
    paper = helper.search_by_title(title)

    if not paper:
        print("エラー: 論文が見つかりませんでした。")
        return None

    if not helper.validate_title(title, paper):
        print("エラー: タイトルが一致しません。")
        print(f"  入力: {title}")
        print(f"  取得: {paper.get('title')}")
        return None

    print(f"論文が見つかりました: {paper.get('title')}")

    bibtex = helper.get_bibtex(paper)
    authors = helper.format_authors(paper)
    venue = helper.format_venue(paper)
    year = helper.format_year(paper)
    doi = helper.get_doi(paper)
    pdf_url = helper.get_pdf_url(paper)

    saved_pdf_path = None
    if pdf_url:
        print(f"PDF をダウンロード中: {pdf_url}")
        PDF_DIR.mkdir(exist_ok=True)
        success = helper.download_pdf(pdf_url, dest=str(pdf_path))
        if success:
            print(f"PDF を {pdf_path} に保存しました。")
            saved_pdf_path = str(pdf_path)
        else:
            print("警告: PDF のダウンロードに失敗しました。")
    else:
        print("警告: オープンアクセス PDF が見つかりませんでした。")

    entry = {
        "bibtex": bibtex,
        "authors": authors,
        "venue": venue,
        "year": year,
        "doi": doi,
        "pdf_url": pdf_url,
        "pdf_path": saved_pdf_path,
    }
    scholar_data[title] = entry
    print(f"scholar_data.json に保存しました: {title}")
    return entry


def main() -> None:
    """メイン処理。CLI 引数の論文タイトル（複数可）で検索し scholar_data.json に追記する。

    1件のタイトルが失敗しても残りのタイトルの処理を継続する。
    """
    if len(sys.argv) < 2:
        print('使い方: python fetch.py "タイトル1" ["タイトル2" ...]')
        sys.exit(1)

    load_dotenv()
    titles = sys.argv[1:]
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    scholar_data = load_scholar_data()
    failed_titles = []

    for title in titles:
        print(f"--- {title} ---")
        try:
            result = fetch_one(title, api_key, scholar_data)
            if result is None:
                failed_titles.append(title)
        except Exception as e:
            print(f"エラー: {title} の取得に失敗しました。{e}")
            failed_titles.append(title)
        save_scholar_data(scholar_data)

    if failed_titles:
        print(f"警告: 以下のタイトルは取得に失敗しました: {failed_titles}")
        sys.exit(1)


if __name__ == "__main__":
    main()
