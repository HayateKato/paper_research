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
    response = client.pages.create(
        parent={"database_id": database_id},
        properties=_build_db_properties(data),
    )
    return response["id"]


def create_page_body(client: Client, page_id: str, data: dict) -> None:
    """Notion ページ本文に論文整理ブロックを書き込む。

    Args:
        client: Notion クライアント
        page_id: 書き込み先ページの ID
        data: output.json のトップレベル辞書（page キーを含む）

    Raises:
        notion_client.errors.APIResponseError: Notion API エラー時
    """
    blocks = _build_page_blocks(data["page"])
    client.blocks.children.append(block_id=page_id, children=blocks)


def _build_db_properties(data: dict) -> dict:
    """DB エントリのプロパティ辞書を構築する。

    Args:
        data: output.json のトップレベル辞書

    Returns:
        Notion API に渡すプロパティ辞書
    """
    return {
        "Title": {"title": [{"text": {"content": data["title"]}}]},
        "Status": {"select": {"name": "Done"}},
        "Tasks": {"multi_select": [{"name": t} for t in data["tasks"]]},
        "Method": {"multi_select": [{"name": m} for m in data["method"]]},
        "Data": {"multi_select": [{"name": d} for d in data["data_domains"]]},
        "Year": {"number": data["year"]},
        "Venue": {"rich_text": [{"text": {"content": data["venue"] or ""}}]},
    }


def _build_page_blocks(page: dict) -> list:
    """ページ本文のブロックリストを構築する。

    Args:
        page: data["page"] の辞書

    Returns:
        Notion API に渡すブロックリスト
    """
    def h2(text: str) -> dict:
        return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": text}}]}}

    def h3(text: str) -> dict:
        return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"text": {"content": text}}]}}

    def p(text: str) -> dict:
        return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": text}}]}}

    def bullet(text: str) -> dict:
        return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"text": {"content": text}}]}}

    purpose = page["purpose"]
    method = page["method"]
    experiment = page["experiment"]
    applicability = page["applicability"]

    blocks = [
        h2("目的"),
        bullet(f"課題：{purpose['issue']}"),
        bullet(f"目標：{purpose['goal']}"),
        h3("新規性"),
        bullet(f"{purpose['new']}"),
        h2("提案手法"),
        h3("処理フロー"),
        p(f"{method['framework']}"),
        h3("使用モデル"),
    ]

    for m in method["models"]:
        blocks.append(bullet(f"{m['model']}（{m['purpose']}）"))

    blocks.append(h3("入力"))
    graph = method["input"]["graph"]
    blocks.append(bullet(f"グラフ構造：ノード：{graph['node']} / エッジ：{graph['edge']}"))

    if method["input"]["others"] is not None:
        blocks.append(bullet(f"その他：{method['input']['others']}"))

    blocks.append(h3("出力"))
    blocks.append(p(f"{method['output']}"))
    blocks.append(h2("実験"))
    blocks.append(h3("データセット"))

    for ds in experiment["datasets"]:
        blocks.append(bullet(f"名称：{ds['name']} / ドメイン：{ds['domain']} / 規模：{ds['scale']}"))

    blocks.append(bullet(f"予測タスク：{experiment['task']}"))
    blocks.append(bullet(f"立証されたこと：{experiment['findings']}"))
    blocks.append(h2("特許ネットワークへの応用可能性"))
    blocks.append(bullet(f"応用できる点：{applicability['applicable'] or 'なし'}"))
    blocks.append(bullet(f"課題・制約：{applicability['limitations'] or 'なし'}"))

    return blocks
