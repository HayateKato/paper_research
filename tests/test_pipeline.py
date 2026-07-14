"""pipeline.py のテスト。"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import pipeline

VALID_SUMMARY = {
    "title": "Test Paper",
    "page": {
        "purpose": {"issue": "課題", "goal": "目標", "new": "新規性"},
        "method": {
            "framework": "処理フロー",
            "models": [{"model": "GCN", "purpose": "特徴抽出"}],
            "input": {"node": "特許", "edge": "引用", "others": None},
            "output": "埋め込みベクトル",
        },
        "experiment": {
            "datasets": [{"name": "USPTO", "domain": "特許", "scale": "100k"}],
            "task": "リンク予測",
            "findings": "SOTA達成",
        },
        "applicability": {"applicable": "応用可能", "limitations": "制約あり"},
    },
}


class TestParseArgs:
    def test_single_title(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["pipeline.py", "Title A"])
        args = pipeline.parse_args()
        assert args.titles == ["Title A"]
        assert args.with_summary is False

    def test_multiple_titles(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["pipeline.py", "Title A", "Title B"])
        args = pipeline.parse_args()
        assert args.titles == ["Title A", "Title B"]

    def test_with_summary_flag(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["pipeline.py", "Title A", "--with-summary"])
        args = pipeline.parse_args()
        assert args.with_summary is True


class TestParseNotebooklmJson:
    def test_valid_json(self):
        text = json.dumps(VALID_SUMMARY)
        result = pipeline.parse_notebooklm_json(text)
        assert result["title"] == "Test Paper"

    def test_markdown_fence_stripped(self):
        text = f"```json\n{json.dumps(VALID_SUMMARY)}\n```"
        result = pipeline.parse_notebooklm_json(text)
        assert result["title"] == "Test Paper"

    def test_invalid_json_returns_none(self):
        assert pipeline.parse_notebooklm_json("not json") is None

    def test_missing_required_key_returns_none(self):
        data = {k: v for k, v in VALID_SUMMARY.items() if k != "page"}
        assert pipeline.parse_notebooklm_json(json.dumps(data)) is None


class TestProcessTitle:
    def test_creates_entry_without_pdf(self):
        client = MagicMock()
        client.pages.create.return_value = {"id": "page-123"}
        scholar = {"venue": "NeurIPS", "year": 2024, "bibtex": None, "authors": [], "doi": None, "pdf_path": None}
        page_id = pipeline.process_title(client, "db-abc", "api-key", "Test Paper", scholar)
        assert page_id == "page-123"

    def test_uploads_pdf_when_path_exists(self, tmp_path):
        client = MagicMock()
        client.pages.create.return_value = {"id": "page-123"}
        pdf_path = tmp_path / "Test Paper.pdf"
        pdf_path.write_bytes(b"dummy")
        scholar = {"venue": None, "year": None, "bibtex": None, "authors": [], "doi": None, "pdf_path": str(pdf_path)}
        with patch("pipeline.upload_pdf", return_value="upload-id-1") as mock_upload:
            pipeline.process_title(client, "db-abc", "api-key", "Test Paper", scholar)
        mock_upload.assert_called_once_with("api-key", str(pdf_path))


class TestFinalizeTitle:
    def test_missing_summary_file_marks_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        client = MagicMock()
        result = pipeline.finalize_title(client, "page-123", "Test Paper")
        assert result is False
        client.pages.update.assert_called_once()
        assert client.pages.update.call_args[1]["properties"]["Status"]["status"]["name"] == "エラー"

    def test_empty_summary_file_marks_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "summary").mkdir()
        (tmp_path / "summary" / "Test Paper.txt").write_text("", encoding="utf-8")
        client = MagicMock()
        result = pipeline.finalize_title(client, "page-123", "Test Paper")
        assert result is False

    def test_valid_summary_writes_body_and_completes(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "summary").mkdir()
        (tmp_path / "summary" / "Test Paper.txt").write_text(
            json.dumps(VALID_SUMMARY), encoding="utf-8"
        )
        client = MagicMock()
        result = pipeline.finalize_title(client, "page-123", "Test Paper")
        assert result is True
        client.blocks.children.append.assert_called_once()
        assert client.pages.update.call_args[1]["properties"]["Status"]["status"]["name"] == "完了"


class TestMain:
    def test_multiple_titles_one_failure_continues(self, tmp_path, monkeypatch):
        """1件のタイトルにscholarデータがなくても残りは処理を継続することを確認。"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("NOTION_API_KEY", "key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "db")
        monkeypatch.setattr(sys, "argv", ["pipeline.py", "Good Paper", "Bad Paper"])

        scholar_data = {
            "Good Paper": {
                "bibtex": None, "authors": [], "venue": None, "year": None,
                "doi": None, "pdf_url": None, "pdf_path": None,
            }
        }
        (tmp_path / "scholar_data.json").write_text(json.dumps(scholar_data), encoding="utf-8")

        mock_client_instance = MagicMock()
        mock_client_instance.pages.create.return_value = {"id": "page-1"}

        with patch("pipeline.subprocess.run"), \
             patch("pipeline.Client", return_value=mock_client_instance):
            with pytest.raises(SystemExit) as exc_info:
                pipeline.main()

        assert exc_info.value.code == 1
