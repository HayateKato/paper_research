"""Semantic Scholar API ラッパー。論文メタデータ取得と PDF ダウンロードを担当する。"""

import re
import time

import requests


class ScholarHelper:
    """Semantic Scholar Graph API のラッパークラス。"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    MATCH_FIELDS = "title,citationStyles,openAccessPdf"
    MAX_RETRIES = 2

    def __init__(self, api_key: str | None = None) -> None:
        self._headers = {"x-api-key": api_key} if api_key else {}

    def _get_with_retry(self, url: str, params: dict, timeout: int = 10) -> requests.Response:
        """429 時に Retry-After 秒待機してリトライする GET リクエスト。

        Raises:
            requests.HTTPError: MAX_RETRIES 回失敗した場合、または 429 以外の HTTP エラー
        """
        for attempt in range(self.MAX_RETRIES):
            resp = requests.get(url, params=params, headers=self._headers, timeout=timeout)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 60))
                print(f"レートリミット超過。{wait} 秒待機してリトライします... ({attempt + 1}/{self.MAX_RETRIES})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        resp.raise_for_status()
        return resp

    def search_by_title(self, title: str) -> dict | None:
        """タイトルで論文を検索する（/paper/search/match エンドポイント使用）。

        Args:
            title: 検索する論文タイトル

        Returns:
            ヒットした論文の辞書（title, citationStyles, openAccessPdf を含む）。
            見つからない場合は None。

        Raises:
            requests.RequestException: API リクエスト失敗時
        """
        resp = self._get_with_retry(
            f"{self.BASE_URL}/paper/search/match",
            params={"query": title, "fields": self.MATCH_FIELDS},
        )
        data = resp.json()
        papers = data.get("data", [])
        return papers[0] if papers else None

    def validate_title(self, query: str, paper: dict) -> bool:
        """入力タイトルとレスポンスのタイトルを正規化して一致確認する。

        Args:
            query: 検索に使ったタイトル
            paper: search_by_title の返り値

        Returns:
            タイトルが一致すれば True
        """
        def normalize(s: str) -> str:
            return re.sub(r"[^a-z0-9]", "", s.lower())

        return normalize(query) == normalize(paper.get("title", ""))

    def get_bibtex(self, paper: dict) -> str | None:
        """citationStyles から BibTeX 文字列を取得する。

        Args:
            paper: search_by_title の返り値

        Returns:
            BibTeX 文字列。取得できない場合は None。
        """
        return paper.get("citationStyles", {}).get("bibtex")

    def get_pdf_url(self, paper: dict) -> str | None:
        """検索結果から openAccessPdf URL を抽出する。

        Args:
            paper: search_by_title の返り値

        Returns:
            PDF の URL。オープンアクセスでない場合は None。
        """
        pdf = paper.get("openAccessPdf")
        if pdf and isinstance(pdf, dict):
            return pdf.get("url")
        return None

    def _parse_bibtex_field(self, bibtex: str, field: str) -> str | None:
        """BibTeX 文字列から指定フィールドの値を抽出する。

        Args:
            bibtex: BibTeX 文字列
            field: 抽出するフィールド名（例: "author", "year"）

        Returns:
            フィールドの値。見つからない場合は None。
        """
        pattern = rf"{re.escape(field)}\s*=\s*\{{([^}}]+)\}}"
        m = re.search(pattern, bibtex, re.IGNORECASE)
        return m.group(1).strip() if m else None

    def format_authors(self, paper: dict) -> list[str]:
        """BibTeX の author フィールドを ['Author A', 'Author B'] の形式で返す。

        Args:
            paper: search_by_title の返り値

        Returns:
            著者名のリスト
        """
        bibtex = self.get_bibtex(paper) or ""
        raw = self._parse_bibtex_field(bibtex, "author")
        if not raw:
            return []
        return [a.strip() for a in raw.split(" and ") if a.strip()]

    def format_venue(self, paper: dict) -> str | None:
        """BibTeX の booktitle または journal フィールドを返す。

        Args:
            paper: search_by_title の返り値

        Returns:
            会議・ジャーナル名。取得できない場合は None。
        """
        bibtex = self.get_bibtex(paper) or ""
        return (
            self._parse_bibtex_field(bibtex, "booktitle")
            or self._parse_bibtex_field(bibtex, "journal")
        )

    def format_year(self, paper: dict) -> int | None:
        """BibTeX の year フィールドを整数で返す。

        Args:
            paper: search_by_title の返り値

        Returns:
            出版年。取得できない場合は None。
        """
        bibtex = self.get_bibtex(paper) or ""
        raw = self._parse_bibtex_field(bibtex, "year")
        try:
            return int(raw) if raw else None
        except ValueError:
            return None

    def download_pdf(self, url: str, dest: str = "paper.pdf") -> bool:
        """PDF を url からダウンロードして dest に保存する。

        Args:
            url: PDF の URL
            dest: 保存先ファイルパス

        Returns:
            ダウンロード成功なら True、失敗なら False。
        """
        try:
            resp = requests.get(url, timeout=60, stream=True)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except requests.RequestException:
            return False
