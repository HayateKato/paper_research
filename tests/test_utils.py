"""utils.py のテスト。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils import sanitize_filename


class TestSanitizeFilename:
    def test_removes_forbidden_characters(self):
        """OS予約文字が除去されることを確認。

        / \\ : * ? " < > | を含むタイトルからそれらが取り除かれる必要がある。
        """
        result = sanitize_filename('A/B\\C:D*E?F"G<H>I|J')
        assert set('\\/:*?"<>|') & set(result) == set()

    def test_keeps_normal_title(self):
        """通常のタイトルはそのまま保持されることを確認。"""
        result = sanitize_filename("Attention Is All You Need")
        assert result == "Attention Is All You Need"

    def test_collapses_whitespace(self):
        """連続する空白が1つのスペースにまとめられることを確認。"""
        result = sanitize_filename("A   B\tC")
        assert result == "A B C"

    def test_strips_leading_trailing_dots_and_spaces(self):
        """前後の空白・ドットが除去されることを確認。"""
        result = sanitize_filename("  ..Title..  ")
        assert result == "Title"

    def test_truncates_long_title(self):
        """max_lengthを超えるタイトルが切り詰められることを確認。"""
        title = "A" * 300
        result = sanitize_filename(title, max_length=150)
        assert len(result) == 150

    def test_japanese_title(self):
        """日本語タイトルがそのまま保持されることを確認。"""
        result = sanitize_filename("特許ネットワークにおけるグラフニューラルネットワーク")
        assert result == "特許ネットワークにおけるグラフニューラルネットワーク"

    def test_empty_after_sanitize_returns_untitled(self):
        """禁止文字のみのタイトルがuntitledにフォールバックすることを確認。"""
        result = sanitize_filename('///:::')
        assert result == "untitled"
