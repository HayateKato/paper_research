"""Notion API ラッパー。DB エントリ作成とページ本文書き込みを担当する。"""

from pathlib import Path

import requests
from notion_client import Client

from utils import sanitize_filename, shorten_title


def upload_pdf(api_key: str, pdf_path: str) -> str | None:
    """PDF を Notion Files API でアップロードして file_upload_id を返す。

    Args:
        api_key: Notion API キー
        pdf_path: アップロードする PDF ファイルのパス

    Returns:
        file_upload_id。ファイルが存在しない場合や失敗時は None。

    Raises:
        requests.HTTPError: Notion API エラー時
    """
    path = Path(pdf_path)
    if not path.exists():
        return None

    notion_version = "2022-06-28"
    short_name = f"{shorten_title(path.stem)}.pdf"

    resp = requests.post(
        "https://api.notion.com/v1/file_uploads",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": notion_version,
            "Content-Type": "application/json",
        },
        json={"name": short_name},
    )
    resp.raise_for_status()
    upload_data = resp.json()
    file_upload_id = upload_data["id"]

    with open(path, "rb") as f:
        upload_resp = requests.post(
            f"https://api.notion.com/v1/file_uploads/{file_upload_id}/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": notion_version,
            },
            files={"file": (short_name, f, "application/pdf")},
        )
    upload_resp.raise_for_status()

    return file_upload_id


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


def create_db_entry(
    client: Client,
    database_id: str,
    title: str,
    status: str = "処理中",
    scholar: dict | None = None,
    file_upload_id: str | None = None,
) -> str:
    """Notion DB に新規エントリを作成してページ ID を返す。

    purpose / Data / github プロパティはスクリプトからは一切設定しない
    （常に空欄とし、ユーザーが Notion 上で手動タグ付けする想定）。

    Args:
        client: Notion クライアント
        database_id: 書き込み先 DB の ID
        title: 論文タイトル
        status: 設定するステータス名（例: "処理中", "完了"）
        scholar: scholar_data.json から取得した論文データ（bibtex/authors/venue/year/doi）
        file_upload_id: Notion Files API でアップロードした PDF の ID

    Returns:
        作成したページの ID

    Raises:
        notion_client.errors.APIResponseError: Notion API エラー時
    """
    response = client.pages.create(
        parent={"database_id": database_id},
        properties=_build_db_properties(
            title, status, scholar=scholar, file_upload_id=file_upload_id
        ),
    )
    return response["id"]


def create_page_body(client: Client, page_id: str, data: dict) -> None:
    """Notion ページ本文に論文整理ブロックを書き込む。

    Args:
        client: Notion クライアント
        page_id: 書き込み先ページの ID
        data: NotebookLM の出力の辞書（page キーを含む）

    Raises:
        notion_client.errors.APIResponseError: Notion API エラー時
    """
    blocks = _build_page_blocks(data["page"])
    client.blocks.children.append(block_id=page_id, children=blocks)


def _build_db_properties(
    title: str,
    status: str,
    scholar: dict | None = None,
    file_upload_id: str | None = None,
) -> dict:
    """DB エントリのプロパティ辞書を構築する。

    Args:
        title: 論文タイトル
        status: 設定するステータス名
        scholar: scholar_data.json から取得した論文データ
        file_upload_id: Notion Files API でアップロードした PDF の ID

    Returns:
        Notion API に渡すプロパティ辞書
    """
    venue = (scholar.get("venue") if scholar else None) or ""
    year = scholar.get("year") if scholar else None

    props: dict = {
        "Title": {"title": [{"text": {"content": title}}]},
        "Status": {"status": {"name": status}},
        "Venue": {"rich_text": [{"text": {"content": venue}}]},
    }

    if year is not None:
        props["Year"] = {"number": year}

    if scholar:
        bibtex = scholar.get("bibtex") or ""
        if bibtex:
            props["BibTeX"] = {"rich_text": [{"text": {"content": bibtex}}]}

        authors = scholar.get("authors") or []
        if authors:
            props["Authors"] = {"multi_select": [{"name": a} for a in authors]}

        doi = scholar.get("doi")
        if doi:
            props["DOI"] = {"url": doi}

    if file_upload_id:
        props["PDF"] = {
            "files": [
                {
                    "type": "file_upload",
                    "file_upload": {"id": file_upload_id},
                    "name": f"{shorten_title(sanitize_filename(title))}.pdf",
                }
            ]
        }

    return props


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
