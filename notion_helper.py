"""Notion API ラッパー。DB エントリ作成とページ本文書き込みを担当する。"""

from notion_client import Client


def create_db_entry(client: Client, database_id: str, data: dict) -> str:
    """Notion DB に新規エントリを作成してページ ID を返す。

    Args:
        client: Notion クライアント
        database_id: 書き込み先 DB の ID
        data: output.json のトップレベル辞書

    Returns:
        作成したページの ID

    Raises:
        notion_client.errors.APIResponseError: Notion API エラー時
    """
    pass


def create_page_body(client: Client, page_id: str, data: dict) -> None:
    """Notion ページ本文に論文整理ブロックを書き込む。

    Args:
        client: Notion クライアント
        page_id: 書き込み先ページの ID
        data: output.json のトップレベル辞書（page キーを含む）

    Raises:
        notion_client.errors.APIResponseError: Notion API エラー時
    """
    pass


def _build_db_properties(data: dict) -> dict:
    """DB エントリのプロパティ辞書を構築する。

    Args:
        data: output.json のトップレベル辞書

    Returns:
        Notion API に渡すプロパティ辞書
    """
    pass


def _build_page_blocks(page: dict) -> list:
    """ページ本文のブロックリストを構築する。

    Args:
        page: data["page"] の辞書

    Returns:
        Notion API に渡すブロックリスト
    """
    pass
