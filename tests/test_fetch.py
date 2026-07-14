"""fetch.py のテスト。"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import fetch

PAPER = {
    "title": "Test Paper",
    "citationStyles": {
        "bibtex": (
            "@Article{Smith2024,\n"
            " author = {Alice Smith},\n"
            " booktitle = {NeurIPS},\n"
            " year = {2024}\n"
            "}\n"
        )
    },
    "externalIds": {"DOI": "10.1145/1234567"},
    "openAccessPdf": {"url": "https://example.com/paper.pdf"},
}


class TestFetchOne:
    def test_new_title_saves_entry(self, tmp_path, monkeypatch):
        """新規タイトルを検索成功した場合にscholar_dataへ保存されることを確認。

        bibtex/authors/venue/year/doi/pdf_url/pdf_pathが全て記録される必要がある。
        """
        monkeypatch.chdir(tmp_path)
        scholar_data = {}
        with patch.object(fetch.ScholarHelper, "search_by_title", return_value=PAPER), \
             patch.object(fetch.ScholarHelper, "download_pdf", return_value=True):
            result = fetch.fetch_one("Test Paper", None, scholar_data)

        assert result is not None
        assert result["doi"] == "10.1145/1234567"
        assert result["venue"] == "NeurIPS"
        assert result["year"] == 2024
        assert result["pdf_path"] == str(fetch.PDF_DIR / "Test Paper.pdf")
        assert "Test Paper" in scholar_data

    def test_no_hit_returns_none(self, tmp_path, monkeypatch):
        """検索でヒットしなかった場合にNoneを返しscholar_dataを変更しないことを確認。"""
        monkeypatch.chdir(tmp_path)
        scholar_data = {}
        with patch.object(fetch.ScholarHelper, "search_by_title", return_value=None):
            result = fetch.fetch_one("Unknown Paper", None, scholar_data)

        assert result is None
        assert scholar_data == {}

    def test_title_mismatch_returns_none(self, tmp_path, monkeypatch):
        """タイトルが一致しない場合にNoneを返すことを確認。"""
        monkeypatch.chdir(tmp_path)
        scholar_data = {}
        mismatched = {**PAPER, "title": "Completely Different Title"}
        with patch.object(fetch.ScholarHelper, "search_by_title", return_value=mismatched):
            result = fetch.fetch_one("Test Paper", None, scholar_data)

        assert result is None

    def test_cached_title_skips_api(self, tmp_path, monkeypatch):
        """キャッシュ済みタイトルはAPI呼び出しをスキップすることを確認。"""
        monkeypatch.chdir(tmp_path)
        cached_entry = {
            "bibtex": "@article{x}",
            "authors": ["Alice"],
            "venue": "NeurIPS",
            "year": 2024,
            "doi": "10.1145/1234567",
            "pdf_url": "https://example.com/paper.pdf",
            "pdf_path": str(fetch.PDF_DIR / "Test Paper.pdf"),
        }
        (tmp_path / "pdfs").mkdir()
        (tmp_path / "pdfs" / "Test Paper.pdf").write_bytes(b"dummy")
        scholar_data = {"Test Paper": cached_entry}

        with patch.object(fetch.ScholarHelper, "search_by_title") as mock_search:
            result = fetch.fetch_one("Test Paper", None, scholar_data)

        mock_search.assert_not_called()
        assert result == cached_entry


class TestMain:
    def test_partial_failure_continues_processing(self, tmp_path, monkeypatch, capsys):
        """複数タイトルのうち1件が失敗しても残りを処理し続けることを確認。"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["fetch.py", "Good Paper", "Bad Paper"])

        def fake_search(self, title):
            return PAPER if title == "Good Paper" else None

        with patch.object(fetch.ScholarHelper, "search_by_title", fake_search), \
             patch.object(fetch.ScholarHelper, "validate_title", return_value=True), \
             patch.object(fetch.ScholarHelper, "download_pdf", return_value=True):
            with pytest.raises(SystemExit) as exc_info:
                fetch.main()

        assert exc_info.value.code == 1
        saved = json.loads((tmp_path / "scholar_data.json").read_text(encoding="utf-8"))
        assert "Good Paper" in saved
        assert "Bad Paper" not in saved
