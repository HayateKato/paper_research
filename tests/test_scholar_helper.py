"""scholar_helper.py のテスト。"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from scholar_helper import ScholarHelper

SEARCH_RESPONSE = {
    "data": [
        {
            "paperId": "paper-abc",
            "authors": [{"authorId": "1", "name": "Alice Smith"}, {"authorId": "2", "name": "Bob Lee"}],
            "openAccessPdf": {"url": "https://example.com/paper.pdf", "status": "GREEN"},
            "publicationVenue": {"id": "v1", "name": "NeurIPS"},
            "s2FieldsOfStudy": [
                {"category": "Computer Science", "source": "s2-fos-model"},
                {"category": "Mathematics", "source": "s2-fos-model"},
                {"category": "Computer Science", "source": "external"},
            ],
        }
    ]
}

BIBTEX_RESPONSE = {
    "citationStyles": {
        "bibtex": "@article{smith2024,\n  title={Test Paper},\n  author={Alice Smith}\n}"
    }
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
            mock_get.return_value = self._make_mock_resp(SEARCH_RESPONSE)
            result = helper.search_by_title("Test Paper")
        assert result["paperId"] == "paper-abc"

    def test_returns_none_when_empty(self):
        helper = ScholarHelper()
        with patch("scholar_helper.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_resp({"data": []})
            result = helper.search_by_title("Unknown Paper")
        assert result is None

    def test_passes_correct_params(self):
        helper = ScholarHelper()
        with patch("scholar_helper.requests.get") as mock_get:
            mock_get.return_value = self._make_mock_resp(SEARCH_RESPONSE)
            helper.search_by_title("My Paper")
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["query"] == "My Paper"
        assert kwargs["params"]["limit"] == 1


class TestGetBibtex:
    def _make_mock_resp(self, json_data):
        mock_resp = MagicMock()
        mock_resp.json.return_value = json_data
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def test_returns_bibtex_string(self):
        helper = ScholarHelper()
        with patch("scholar_helper.requests.get") as mock_get, \
             patch("scholar_helper.time.sleep"):
            mock_get.return_value = self._make_mock_resp(BIBTEX_RESPONSE)
            result = helper.get_bibtex("paper-abc")
        assert "@article" in result

    def test_returns_none_when_missing(self):
        helper = ScholarHelper()
        with patch("scholar_helper.requests.get") as mock_get, \
             patch("scholar_helper.time.sleep"):
            mock_get.return_value = self._make_mock_resp({"citationStyles": {}})
            result = helper.get_bibtex("paper-abc")
        assert result is None

    def test_sleeps_before_request(self):
        helper = ScholarHelper()
        with patch("scholar_helper.requests.get") as mock_get, \
             patch("scholar_helper.time.sleep") as mock_sleep:
            mock_get.return_value = self._make_mock_resp(BIBTEX_RESPONSE)
            helper.get_bibtex("paper-abc")
        mock_sleep.assert_called_once_with(1)


class TestGetPdfUrl:
    def test_returns_url(self):
        helper = ScholarHelper()
        paper = SEARCH_RESPONSE["data"][0]
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
        paper = SEARCH_RESPONSE["data"][0]
        assert helper.format_authors(paper) == ["Alice Smith", "Bob Lee"]

    def test_empty_authors(self):
        helper = ScholarHelper()
        assert helper.format_authors({"authors": []}) == []

    def test_skips_missing_name(self):
        helper = ScholarHelper()
        paper = {"authors": [{"authorId": "1"}, {"authorId": "2", "name": "Bob"}]}
        assert helper.format_authors(paper) == ["Bob"]


class TestFormatVenue:
    def test_returns_publication_venue_name(self):
        helper = ScholarHelper()
        paper = SEARCH_RESPONSE["data"][0]
        assert helper.format_venue(paper) == "NeurIPS"

    def test_falls_back_to_venue_field(self):
        helper = ScholarHelper()
        paper = {"publicationVenue": None, "venue": "ICML 2024"}
        assert helper.format_venue(paper) == "ICML 2024"

    def test_returns_none_when_both_missing(self):
        helper = ScholarHelper()
        assert helper.format_venue({}) is None

    def test_returns_none_when_venue_empty_string(self):
        helper = ScholarHelper()
        paper = {"publicationVenue": None, "venue": ""}
        assert helper.format_venue(paper) is None


class TestFormatFieldsOfStudy:
    def test_deduplicates(self):
        helper = ScholarHelper()
        paper = SEARCH_RESPONSE["data"][0]
        result = helper.format_fields_of_study(paper)
        assert result.count("Computer Science") == 1

    def test_preserves_order(self):
        helper = ScholarHelper()
        paper = SEARCH_RESPONSE["data"][0]
        result = helper.format_fields_of_study(paper)
        assert result[0] == "Computer Science"
        assert result[1] == "Mathematics"

    def test_empty(self):
        helper = ScholarHelper()
        assert helper.format_fields_of_study({}) == []


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
