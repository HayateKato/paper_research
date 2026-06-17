"""scholar_helper.py のテスト。"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from scholar_helper import ScholarHelper

BIBTEX = (
    "@Article{Smith2024,\n"
    " author = {Alice Smith and Bob Lee},\n"
    " booktitle = {NeurIPS},\n"
    " journal = {Journal of AI},\n"
    " title = {Test Paper},\n"
    " year = {2024}\n"
    "}\n"
)

MATCH_RESPONSE = {
    "data": [
        {
            "paperId": "paper-abc",
            "title": "Test Paper",
            "openAccessPdf": {"url": "https://example.com/paper.pdf", "status": "GREEN"},
            "citationStyles": {"bibtex": BIBTEX},
            "matchScore": 150.0,
        }
    ]
}


class TestGetWithRetry:
    def _make_mock_resp(self, status_code: int, json_data: dict = None):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.headers = {}
        if json_data is not None:
            mock_resp.json.return_value = json_data
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def test_retries_on_429(self):
        helper = ScholarHelper()
        mock_429 = self._make_mock_resp(429)
        mock_429.headers = {"Retry-After": "1"}
        mock_ok = self._make_mock_resp(200, {})
        with patch("scholar_helper.requests.get", side_effect=[mock_429, mock_ok]), \
             patch("scholar_helper.time.sleep"):
            resp = helper._get_with_retry("https://example.com", {})
        assert resp == mock_ok

    def test_adds_api_key_header(self):
        helper = ScholarHelper(api_key="test-key")
        mock_ok = self._make_mock_resp(200, {})
        with patch("scholar_helper.requests.get", return_value=mock_ok) as mock_get:
            helper._get_with_retry("https://example.com", {})
        _, kwargs = mock_get.call_args
        assert kwargs["headers"] == {"x-api-key": "test-key"}

    def test_no_api_key_empty_header(self):
        helper = ScholarHelper()
        mock_ok = self._make_mock_resp(200, {})
        with patch("scholar_helper.requests.get", return_value=mock_ok) as mock_get:
            helper._get_with_retry("https://example.com", {})
        _, kwargs = mock_get.call_args
        assert kwargs["headers"] == {}


class TestSearchByTitle:
    def _make_mock_resp(self, json_data):
        mock_resp = MagicMock()
        mock_resp.json.return_value = json_data
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def test_returns_first_result(self):
        helper = ScholarHelper()
        with patch("scholar_helper.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_resp(MATCH_RESPONSE)
            result = helper.search_by_title("Test Paper")
        assert result["title"] == "Test Paper"

    def test_returns_none_when_empty(self):
        helper = ScholarHelper()
        with patch("scholar_helper.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_resp({"data": []})
            result = helper.search_by_title("Unknown Paper")
        assert result is None

    def test_uses_match_endpoint(self):
        helper = ScholarHelper()
        with patch("scholar_helper.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_resp(MATCH_RESPONSE)
            helper.search_by_title("My Paper")
        args, kwargs = mock_get.call_args
        assert "search/match" in args[0]
        assert kwargs["params"]["query"] == "My Paper"


class TestValidateTitle:
    def test_exact_match(self):
        helper = ScholarHelper()
        paper = {"title": "Test Paper"}
        assert helper.validate_title("Test Paper", paper) is True

    def test_case_insensitive(self):
        helper = ScholarHelper()
        paper = {"title": "test paper"}
        assert helper.validate_title("Test Paper", paper) is True

    def test_ignores_punctuation(self):
        helper = ScholarHelper()
        paper = {"title": "Test: A Paper"}
        assert helper.validate_title("Test A Paper", paper) is True

    def test_mismatch_returns_false(self):
        helper = ScholarHelper()
        paper = {"title": "Completely Different Title"}
        assert helper.validate_title("Test Paper", paper) is False


class TestGetBibtex:
    def test_returns_bibtex_from_paper(self):
        helper = ScholarHelper()
        paper = MATCH_RESPONSE["data"][0]
        result = helper.get_bibtex(paper)
        assert "@Article" in result

    def test_returns_none_when_missing(self):
        helper = ScholarHelper()
        assert helper.get_bibtex({"citationStyles": {}}) is None

    def test_returns_none_when_no_citation_styles(self):
        helper = ScholarHelper()
        assert helper.get_bibtex({}) is None


class TestParseBibtexField:
    def test_extracts_author(self):
        helper = ScholarHelper()
        result = helper._parse_bibtex_field(BIBTEX, "author")
        assert result == "Alice Smith and Bob Lee"

    def test_extracts_year(self):
        helper = ScholarHelper()
        result = helper._parse_bibtex_field(BIBTEX, "year")
        assert result == "2024"

    def test_extracts_booktitle(self):
        helper = ScholarHelper()
        result = helper._parse_bibtex_field(BIBTEX, "booktitle")
        assert result == "NeurIPS"

    def test_returns_none_when_field_missing(self):
        helper = ScholarHelper()
        assert helper._parse_bibtex_field(BIBTEX, "nonexistent") is None


class TestGetPdfUrl:
    def test_returns_url(self):
        helper = ScholarHelper()
        paper = MATCH_RESPONSE["data"][0]
        assert helper.get_pdf_url(paper) == "https://example.com/paper.pdf"

    def test_returns_none_when_missing(self):
        helper = ScholarHelper()
        assert helper.get_pdf_url({"openAccessPdf": None}) is None

    def test_returns_none_when_key_absent(self):
        helper = ScholarHelper()
        assert helper.get_pdf_url({}) is None


class TestFormatAuthors:
    def test_returns_names(self):
        helper = ScholarHelper()
        paper = MATCH_RESPONSE["data"][0]
        assert helper.format_authors(paper) == ["Alice Smith", "Bob Lee"]

    def test_empty_when_no_bibtex(self):
        helper = ScholarHelper()
        assert helper.format_authors({}) == []

    def test_empty_when_no_author_field(self):
        helper = ScholarHelper()
        paper = {"citationStyles": {"bibtex": "@article{x, title={T}}"}}
        assert helper.format_authors(paper) == []


class TestFormatVenue:
    def test_returns_booktitle(self):
        helper = ScholarHelper()
        paper = MATCH_RESPONSE["data"][0]
        assert helper.format_venue(paper) == "NeurIPS"

    def test_falls_back_to_journal(self):
        helper = ScholarHelper()
        bibtex = "@article{x, journal = {TPAMI}, title={T}, year={2024}}"
        paper = {"citationStyles": {"bibtex": bibtex}}
        assert helper.format_venue(paper) == "TPAMI"

    def test_returns_none_when_both_missing(self):
        helper = ScholarHelper()
        paper = {"citationStyles": {"bibtex": "@article{x, title={T}}"}}
        assert helper.format_venue(paper) is None


class TestFormatYear:
    def test_returns_year_as_int(self):
        helper = ScholarHelper()
        paper = MATCH_RESPONSE["data"][0]
        assert helper.format_year(paper) == 2024

    def test_returns_none_when_no_year(self):
        helper = ScholarHelper()
        paper = {"citationStyles": {"bibtex": "@article{x, title={T}}"}}
        assert helper.format_year(paper) is None

    def test_returns_none_when_no_bibtex(self):
        helper = ScholarHelper()
        assert helper.format_year({}) is None


class TestDownloadPdf:
    def test_returns_true_on_success(self, tmp_path):
        helper = ScholarHelper()
        dest = str(tmp_path / "paper.pdf")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_content.return_value = [b"PDF content"]
        with patch("scholar_helper.requests.get", return_value=mock_resp):
            result = helper.download_pdf("https://example.com/paper.pdf", dest=dest)
        assert result is True
        assert Path(dest).read_bytes() == b"PDF content"

    def test_returns_false_on_failure(self, tmp_path):
        import requests as req
        helper = ScholarHelper()
        dest = str(tmp_path / "paper.pdf")
        with patch("scholar_helper.requests.get", side_effect=req.RequestException("error")):
            result = helper.download_pdf("https://example.com/paper.pdf", dest=dest)
        assert result is False
