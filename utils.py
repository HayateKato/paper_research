"""ファイル名生成など複数モジュールで共有する共通ユーティリティ。"""

import re


def sanitize_filename(title: str, max_length: int = 150) -> str:
    """論文タイトルをファイル名として安全な文字列に変換する。

    OS 予約文字（/ \\ : * ? " < > |）を除去し、前後の空白・ドットを削り、
    長すぎる場合は max_length で切り詰める。空文字列になった場合は "untitled" を返す。

    Args:
        title (str): 論文タイトル（原文）
        max_length (int): ファイル名の最大文字数

    Returns:
        str: サニタイズ済みのファイル名（拡張子なし）
    """
    sanitized = re.sub(r'[\\/:*?"<>|]', "", title)
    sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
    sanitized = sanitized[:max_length].strip(" .")
    return sanitized or "untitled"


def shorten_title(title: str, max_words: int = 3) -> str:
    """タイトルの先頭 max_words 単語だけを抽出する。

    Notion の file_upload name は長すぎる文字列を渡すと登録に失敗するため、
    PDF をアップロードする際の表示名を短縮する用途で使う。

    Args:
        title (str): 論文タイトル（サニタイズ済みでも可）
        max_words (int): 抽出する単語数

    Returns:
        str: 先頭 max_words 単語を結合した文字列
    """
    words = title.split()
    return " ".join(words[:max_words]) or "untitled"
