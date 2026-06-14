"""main.py のテスト。"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import main


VALID_DATA = {
    "title": "Test Paper",
    "tasks": ["ノード分類"],
    "method": ["GNN"],
    "data_domains": ["特許"],
    "year": 2024,
    "venue": "NeurIPS",
    "page": {
        "purpose": {"issue": "課題", "goal": "目標"},
        "method": {
            "framework": "処理フロー",
            "models": [{"model": "GCN", "purpose": "特徴抽出"}],
            "input": {"graph": {"node": "特許", "edge": "引用"}, "others": None},
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


class TestLoadOutput:
    def test_file_not_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit):
            main.load_output()

    def test_invalid_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output.txt").write_text("not json")
        with pytest.raises(SystemExit):
            main.load_output()

    def test_missing_required_key(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        data = {k: v for k, v in VALID_DATA.items() if k != "title"}
        (tmp_path / "output.txt").write_text(json.dumps(data))
        with pytest.raises(SystemExit):
            main.load_output()

    def test_valid(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output.txt").write_text(json.dumps(VALID_DATA))
        result = main.load_output()
        assert result["title"] == "Test Paper"

    def test_valid_with_markdown_fence(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        content = f"```json\n{json.dumps(VALID_DATA)}\n```"
        (tmp_path / "output.txt").write_text(content)
        result = main.load_output()
        assert result["title"] == "Test Paper"


class TestArchiveOutput:
    def test_copies_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "output.txt").write_text(json.dumps(VALID_DATA))
        main.archive_output()
        assert (tmp_path / "output.txt").exists()
        archived = list((tmp_path / "results").glob("*.txt"))
        assert len(archived) == 1
