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
