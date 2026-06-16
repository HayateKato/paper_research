"""notion_helper.py のテスト。"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import notion_helper

VALID_DATA = {
    "title": "Test Paper",
    "tasks": ["ノード分類"],
    "method": ["GNN"],
    "data_domains": ["特許"],
    "year": 2024,
    "venue": "NeurIPS",
    "page": {
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
    },
}


class TestBuildDbProperties:
    def test_title(self):
        props = notion_helper._build_db_properties(VALID_DATA)
        assert props["Title"]["title"][0]["text"]["content"] == "Test Paper"

    def test_tasks(self):
        props = notion_helper._build_db_properties(VALID_DATA)
        names = [o["name"] for o in props["Tasks"]["multi_select"]]
        assert "ノード分類" in names

    def test_year(self):
        props = notion_helper._build_db_properties(VALID_DATA)
        assert props["Year"]["number"] == 2024

    def test_venue(self):
        props = notion_helper._build_db_properties(VALID_DATA)
        assert props["Venue"]["rich_text"][0]["text"]["content"] == "NeurIPS"

    def test_venue_none(self):
        data = {**VALID_DATA, "venue": None}
        props = notion_helper._build_db_properties(data)
        assert props["Venue"]["rich_text"][0]["text"]["content"] == ""


class TestBuildPageBlocks:
    def setup_method(self):
        self.blocks = notion_helper._build_page_blocks(VALID_DATA["page"])

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
        page = {**VALID_DATA["page"]}
        page["method"] = {**page["method"], "input": {"node": "特許", "edge": "引用", "others": "追加入力"}}
        blocks = notion_helper._build_page_blocks(page)
        bullets = [
            b["bulleted_list_item"]["rich_text"][0]["text"]["content"]
            for b in blocks
            if b["type"] == "bulleted_list_item"
        ]
        assert any("その他" in t for t in bullets)

    def test_applicability_none_becomes_nashi(self):
        page = {**VALID_DATA["page"], "applicability": {"applicable": None, "limitations": None}}
        blocks = notion_helper._build_page_blocks(page)
        paras = [
            b["paragraph"]["rich_text"][0]["text"]["content"]
            for b in blocks
            if b["type"] == "paragraph"
        ]
        assert any("なし" in t for t in paras)


class TestCreateDbEntry:
    def test_calls_api_and_returns_id(self):
        client = MagicMock()
        client.pages.create.return_value = {"id": "page-123"}
        page_id = notion_helper.create_db_entry(client, "db-abc", VALID_DATA)
        assert page_id == "page-123"
        client.pages.create.assert_called_once()


class TestCreatePageBody:
    def test_calls_api(self):
        client = MagicMock()
        notion_helper.create_page_body(client, "page-123", VALID_DATA)
        client.blocks.children.append.assert_called_once()
