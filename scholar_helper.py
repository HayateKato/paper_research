"""Semantic Scholar API ラッパー。論文メタデータ取得と PDF ダウンロードを担当する。"""

import time

import requests


class ScholarHelper:
    """Semantic Scholar Graph API のラッパークラス。"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    SEARCH_FIELDS = "paperId,authors,openAccessPdf,publicationVenue,s2FieldsOfStudy"

    def search_by_title(self, title: str) -> dict | None:
        """タイトルで論文を検索する。

        Args:
            title: 検索する論文タイトル

        Returns:
            ヒットした論文の辞書（paperId, authors, openAccessPdf,
            publicationVenue, s2FieldsOfStudy を含む）。見つからない場合は None。

        Raises:
            requests.RequestException: API リクエスト失敗時
        """
        resp = requests.get(
            f"{self.BASE_URL}/paper/search",
            params={"query": title, "fields": self.SEARCH_FIELDS, "limit": 1},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        papers = data.get("data", [])
        return papers[0] if papers else None

    def get_bibtex(self, paper_id: str) -> str | None:
        """paperId から BibTeX 文字列を取得する。

        Args:
            paper_id: Semantic Scholar の論文 ID

        Returns:
            BibTeX 文字列。取得できない場合は None。

        Raises:
            requests.RequestException: API リクエスト失敗時
        """
        time.sleep(1)
        resp = requests.get(
            f"{self.BASE_URL}/paper/{paper_id}",
            params={"fields": "citationStyles"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("citationStyles", {}).get("bibtex")

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

    def format_authors(self, paper: dict) -> list[str]:
        """authors リストを ['Author A', 'Author B'] の形式で返す。

        Args:
            paper: search_by_title の返り値

        Returns:
            著者名のリスト
        """
        authors = paper.get("authors", [])
        return [a["name"] for a in authors if a.get("name")]

    def format_venue(self, paper: dict) -> str | None:
        """publicationVenue.name を返す。なければ venue フィールドを返す。

        Args:
            paper: search_by_title の返り値

        Returns:
            会議・ジャーナル名。取得できない場合は None。
        """
        venue = paper.get("publicationVenue")
        if venue and isinstance(venue, dict):
            name = venue.get("name")
            if name:
                return name
        return paper.get("venue") or None

    def format_fields_of_study(self, paper: dict) -> list[str]:
        """s2FieldsOfStudy の category を重複除去して返す。

        Args:
            paper: search_by_title の返り値

        Returns:
            研究分野のリスト（重複なし）
        """
        fields = paper.get("s2FieldsOfStudy", [])
        seen: set[str] = set()
        result: list[str] = []
        for f in fields:
            cat = f.get("category")
            if cat and cat not in seen:
                seen.add(cat)
                result.append(cat)
        return result

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
