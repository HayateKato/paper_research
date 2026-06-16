"""Notion API ラッパー。DB エントリ作成とページ本文書き込みを担当する。"""

from notion_client import Client


def update_page_status(client: Client, page_id: str, status: str) -> None:
    """Notion ページの Status プロパティを更新する。

    Args:
        client: Notion クライアント
        page_id: 更新対象ページの ID
        status: 設定するステータス名（例: "完了", "エラー"）
    """
    client.pages.update(
        page_id=page_id,
        properties={"Status": {"status": {"name": status}}},
    )


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
        "Status": {"status": {"name": "完了"}},
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

    def numbered(text: str) -> dict:
        return {"object": "block", "type": "numbered_list_item", "numbered_list_item": {"rich_text": [{"text": {"content": text}}]}}

    def framework_blocks(text: str) -> list:
        import re
        parts = re.split(r'(?=\d+\. )', text.strip())
        parts = [re.sub(r'^\d+\. ', '', s).strip() for s in parts if s.strip()]
        return [numbered(s) for s in parts] if len(parts) > 1 else [p(text)]

    def table(datasets: list) -> dict:
        def cell(text: str) -> list:
            return [{"type": "text", "text": {"content": text}}]

        header = {
            "type": "table_row",
            "table_row": {"cells": [cell("名称"), cell("ドメイン"), cell("規模")]},
        }
        rows = [
            {
                "type": "table_row",
                "table_row": {"cells": [cell(ds["name"]), cell(ds["domain"]), cell(ds["scale"])]},
            }
            for ds in datasets
        ]
        return {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": 3,
                "has_column_header": True,
                "has_row_header": False,
                "children": [header] + rows,
            },
        }

    purpose = page["purpose"]
    method = page["method"]
    experiment = page["experiment"]
    applicability = page["applicability"]
    related_works = page.get("related_works", [])

    blocks = [
        h2("概要"),
        h3("課題"),
        p(purpose["issue"]),
        h3("目標"),
        p(purpose["goal"]),
        h3("新規性"),
        p(purpose["new"]),
        h2("提案手法"),
        h3("処理フロー"),
        *framework_blocks(method["framework"]),
        h3("使用モデル"),
    ]

    for m in method["models"]:
        blocks.append(bullet(f"{m['model']}：{m['purpose']}）"))

    inp = method["input"]
    blocks.append(h3("入力"))
    blocks.append(bullet(f"ノード：{inp['node']}"))
    if inp.get("edge"):
        blocks.append(bullet(f"エッジ：{inp['edge']}"))
    if inp.get("others"):
        blocks.append(bullet(f"その他：{inp['others']}"))

    blocks.append(h3("出力"))
    blocks.append(p(method["output"]))
    blocks.append(h2("実験"))
    blocks.append(h3("データセット"))
    blocks.append(table(experiment["datasets"]))
    blocks.append(h3("予測タスク"))
    blocks.append(p(experiment["task"]))
    blocks.append(h3("立証されたこと"))
    blocks.append(p(experiment["findings"]))
    blocks.append(h2("特許ネットワークへの応用可能性"))
    blocks.append(h3("応用できる点"))
    blocks.append(p(applicability["applicable"] or "なし"))
    blocks.append(h3("課題・制約"))
    blocks.append(p(applicability["limitations"] or "なし"))

    if related_works:
        blocks.append(h2("関連研究"))
        for rw in related_works:
            blocks.append(h3(rw["title"]))
            blocks.append(p(rw["relation"]))

    return blocks
