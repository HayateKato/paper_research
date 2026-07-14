"""notion_helper.py のテスト。"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import notion_helper

PAGE_DATA = {
    "purpose": {"issue": "課題", "goal": "目標", "new": "新規性の説明"},
    "method": {
        "framework": "処理フロー",
        "models": [{"model": "GCN", "purpose": "特徴抽出"}],
        "input": {"node": "特許", "edge": "引用", "others": None},
        "output": "埋め込みベクトル",
    },
    "experiment": {
        "datasets": [{"name": "USPTO", "domain": "特許", "scale": "100k nodes"}],
        "task": "リンク予測",
        "findings": "SOTAを達成",
    },
    "applicability": {"applicable": "応用可能", "limitations": "制約あり"},
}

VALID_DATA = {"title": "Test Paper", "page": PAGE_DATA}


class TestBuildDbProperties:
    def test_title(self):
        props = notion_helper._build_db_properties("Test Paper", "処理中")
        assert props["Title"]["title"][0]["text"]["content"] == "Test Paper"

    def test_status(self):
        props = notion_helper._build_db_properties("Test Paper", "処理中")
        assert props["Status"]["status"]["name"] == "処理中"

    def test_no_tasks_method_data_properties(self):
        """Tasks/Method/Dataプロパティが一切設定されないことを確認（新スキーマでは廃止）。"""
        props = notion_helper._build_db_properties("Test Paper", "完了")
        assert "Tasks" not in props
        assert "Method" not in props
        assert "Data" not in props

    def test_no_purpose_or_github_properties(self):
        """purpose/githubプロパティが一切設定されないことを確認（常に空欄）。"""
        scholar = {"venue": "NeurIPS", "year": 2024, "doi": "10.1145/1234567"}
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar=scholar)
        assert "purpose" not in props
        assert "github" not in props

    def test_year_from_scholar(self):
        scholar = {"year": 2024, "venue": None}
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar=scholar)
        assert props["Year"]["number"] == 2024

    def test_year_absent_when_no_scholar(self):
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar=None)
        assert "Year" not in props

    def test_year_absent_when_scholar_has_no_year(self):
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar={"venue": "X"})
        assert "Year" not in props

    def test_venue_from_scholar(self):
        scholar = {"venue": "NeurIPS", "year": None}
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar=scholar)
        assert props["Venue"]["rich_text"][0]["text"]["content"] == "NeurIPS"

    def test_venue_empty_when_no_scholar(self):
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar=None)
        assert props["Venue"]["rich_text"][0]["text"]["content"] == ""


class TestBuildPageBlocks:
    def setup_method(self):
        self.blocks = notion_helper._build_page_blocks(PAGE_DATA)

    def _block_texts(self, type_: str) -> list[str]:
        return [
            b[type_]["rich_text"][0]["text"]["content"]
            for b in self.blocks
            if b["type"] == type_
        ]

    def test_headings_h2(self):
        texts = [
            b["heading_2"]["rich_text"][0]["text"]["content"]
            for b in self.blocks
            if b["type"] == "heading_2"
        ]
        assert "概要" in texts
        assert "提案手法" in texts
        assert "実験" in texts
        assert "特許ネットワークへの応用可能性" in texts

    def test_headings_h3(self):
        texts = [
            b["heading_3"]["rich_text"][0]["text"]["content"]
            for b in self.blocks
            if b["type"] == "heading_3"
        ]
        assert "新規性" in texts
        assert "処理フロー" in texts
        assert "使用モデル" in texts
        assert "入力" in texts
        assert "出力" in texts
        assert "データセット" in texts

    def test_purpose_paragraphs(self):
        paras = self._block_texts("paragraph")
        assert any("課題" in t for t in paras)
        assert any("目標" in t for t in paras)
        assert any("新規性の説明" in t for t in paras)

    def test_models_expanded(self):
        bullets = self._block_texts("bulleted_list_item")
        assert any("GCN" in t for t in bullets)

    def test_others_omitted_when_null(self):
        bullets = self._block_texts("bulleted_list_item")
        assert not any("その他" in t for t in bullets)

    def test_others_included_when_not_null(self):
        page = {**PAGE_DATA}
        page["method"] = {**page["method"], "input": {"node": "特許", "edge": "引用", "others": "追加入力"}}
        blocks = notion_helper._build_page_blocks(page)
        bullets = [
            b["bulleted_list_item"]["rich_text"][0]["text"]["content"]
            for b in blocks
            if b["type"] == "bulleted_list_item"
        ]
        assert any("その他" in t for t in bullets)

    def test_applicability_none_becomes_nashi(self):
        page = {**PAGE_DATA, "applicability": {"applicable": None, "limitations": None}}
        blocks = notion_helper._build_page_blocks(page)
        paras = [
            b["paragraph"]["rich_text"][0]["text"]["content"]
            for b in blocks
            if b["type"] == "paragraph"
        ]
        assert any("なし" in t for t in paras)


class TestBuildDbPropertiesWithScholar:
    SCHOLAR = {
        "bibtex": "@article{test2024, title={Test}}",
        "authors": ["Alice Smith", "Bob Lee"],
        "venue": "NeurIPS 2024",
        "year": 2024,
        "doi": "10.1145/1234567",
        "pdf_url": "https://example.com/paper.pdf",
    }

    def test_bibtex_added(self):
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar=self.SCHOLAR)
        assert props["BibTeX"]["rich_text"][0]["text"]["content"] == self.SCHOLAR["bibtex"]

    def test_authors_multi_select(self):
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar=self.SCHOLAR)
        names = [o["name"] for o in props["Authors"]["multi_select"]]
        assert "Alice Smith" in names
        assert "Bob Lee" in names

    def test_doi_added(self):
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar=self.SCHOLAR)
        assert props["DOI"]["url"] == "10.1145/1234567"

    def test_doi_absent_when_no_doi(self):
        scholar = {**self.SCHOLAR, "doi": None}
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar=scholar)
        assert "DOI" not in props

    def test_pdf_file_upload(self):
        props = notion_helper._build_db_properties(
            "Test Paper", "完了", scholar=self.SCHOLAR, file_upload_id="upload-id-123"
        )
        assert props["PDF"]["files"][0]["file_upload"]["id"] == "upload-id-123"

    def test_pdf_file_name_uses_sanitized_title(self):
        props = notion_helper._build_db_properties(
            "A/B: Test Paper", "完了", scholar=self.SCHOLAR, file_upload_id="upload-id-123"
        )
        assert props["PDF"]["files"][0]["name"] == "AB Test Paper.pdf"

    def test_venue_from_scholar(self):
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar=self.SCHOLAR)
        assert props["Venue"]["rich_text"][0]["text"]["content"] == "NeurIPS 2024"

    def test_year_from_scholar(self):
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar=self.SCHOLAR)
        assert props["Year"]["number"] == 2024

    def test_no_scholar_no_extra_props(self):
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar=None)
        assert "BibTeX" not in props
        assert "Authors" not in props
        assert "DOI" not in props
        assert "PDF" not in props
        assert "Year" not in props

    def test_no_file_upload_id_no_pdf(self):
        props = notion_helper._build_db_properties("Test Paper", "完了", scholar=self.SCHOLAR)
        assert "PDF" not in props


class TestCreateDbEntry:
    def test_calls_api_and_returns_id(self):
        client = MagicMock()
        client.pages.create.return_value = {"id": "page-123"}
        page_id = notion_helper.create_db_entry(client, "db-abc", "Test Paper")
        assert page_id == "page-123"
        client.pages.create.assert_called_once()

    def test_default_status_is_shori_chu(self):
        client = MagicMock()
        client.pages.create.return_value = {"id": "page-123"}
        notion_helper.create_db_entry(client, "db-abc", "Test Paper")
        call_kwargs = client.pages.create.call_args[1]
        assert call_kwargs["properties"]["Status"]["status"]["name"] == "処理中"

    def test_passes_scholar_data(self):
        client = MagicMock()
        client.pages.create.return_value = {"id": "page-123"}
        scholar = {"bibtex": "@article{}", "authors": ["Alice"], "venue": None, "year": None}
        notion_helper.create_db_entry(client, "db-abc", "Test Paper", scholar=scholar)
        call_kwargs = client.pages.create.call_args[1]
        assert "BibTeX" in call_kwargs["properties"]


class TestCreatePageBody:
    def test_calls_api(self):
        client = MagicMock()
        notion_helper.create_page_body(client, "page-123", VALID_DATA)
        client.blocks.children.append.assert_called_once()
