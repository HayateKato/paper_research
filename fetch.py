"""Semantic Scholar から論文メタデータと PDF を取得するスクリプト。

使い方: python fetch.py "論文タイトル"
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from scholar_helper import ScholarHelper

SCHOLAR_DATA_FILE = Path("scholar_data.json")
PDF_FILE = "paper.pdf"


def load_scholar_data() -> dict:
    """scholar_data.json を読み込む。ファイルがない場合は空辞書を返す。

    Returns:
        タイトルをキーとした論文データの辞書
    """
    if SCHOLAR_DATA_FILE.exists():
        return json.loads(SCHOLAR_DATA_FILE.read_text(encoding="utf-8"))
    return {}


def save_scholar_data(data: dict) -> None:
    """scholar_data.json に data を保存する。

    Args:
        data: タイトルをキーとした論文データの辞書
    """
    SCHOLAR_DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    """メイン処理。CLI 引数の論文タイトルで検索し scholar_data.json に追記する。"""
    if len(sys.argv) < 2:
        print("使い方: python fetch.py \"論文タイトル\"")
        sys.exit(1)

    load_dotenv()
    title = sys.argv[1]
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    scholar_data = load_scholar_data()
    if title in scholar_data:
        print(f"キャッシュ済み: {title}（API スキップ）")
        cached = scholar_data[title]
        pdf_url = cached.get("pdf_url")
        if pdf_url and not Path(PDF_FILE).exists():
            print(f"PDF を再ダウンロード中: {pdf_url}")
            helper = ScholarHelper(api_key=api_key)
            success = helper.download_pdf(pdf_url, dest=PDF_FILE)
            if success:
                print(f"PDF を {PDF_FILE} に保存しました。")
            else:
                print("警告: PDF のダウンロードに失敗しました。")
        return

    helper = ScholarHelper(api_key=api_key)

    print(f"Semantic Scholar で検索中: {title}")
    try:
        paper = helper.search_by_title(title)
    except Exception as e:
        print(f"エラー: Semantic Scholar 検索に失敗しました。{e}")
        sys.exit(1)

    if not paper:
        print("エラー: 論文が見つかりませんでした。")
        sys.exit(1)

    if not helper.validate_title(title, paper):
        print(f"エラー: タイトルが一致しません。")
        print(f"  入力: {title}")
        print(f"  取得: {paper.get('title')}")
        sys.exit(1)

    print(f"論文が見つかりました: {paper.get('title')}")

    bibtex = helper.get_bibtex(paper)
    authors = helper.format_authors(paper)
    venue = helper.format_venue(paper)
    year = helper.format_year(paper)
    pdf_url = helper.get_pdf_url(paper)

    if pdf_url:
        print(f"PDF をダウンロード中: {pdf_url}")
        success = helper.download_pdf(pdf_url, dest=PDF_FILE)
        if success:
            print(f"PDF を {PDF_FILE} に保存しました。")
        else:
            print("警告: PDF のダウンロードに失敗しました。")
            pdf_url = None
    else:
        print("警告: オープンアクセス PDF が見つかりませんでした。")

    scholar_data = load_scholar_data()
    scholar_data[title] = {
        "bibtex": bibtex,
        "authors": authors,
        "venue": venue,
        "year": year,
        "pdf_url": pdf_url,
    }
    save_scholar_data(scholar_data)
    print(f"scholar_data.json に保存しました: {title}")


if __name__ == "__main__":
    main()
