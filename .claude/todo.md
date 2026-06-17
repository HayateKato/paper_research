# TODO.md

タスク管理ファイル。コンテキストをリセットしても、このファイルを読めば作業を再開できる状態に保つ。

## ステータス凡例

- `[ ]` 未着手
- `[~]` 進行中
- `[x]` 完了

## タスク

### Semantic Scholar 連携機能（fetch.py / scholar_helper.py）

- [x] spec.md を更新（2スクリプト構成・新 Notion DB スキーマ）
- [x] scholar_helper.py 新規作成（ScholarHelper クラス）
- [x] fetch.py 新規作成（CLI スクリプト）
- [x] notion_helper.py 更新（upload_pdf, _build_db_properties 拡張）
- [x] main.py 更新（load_scholar_data, PDF アップロードフロー追加）
- [x] テストコード追加（test_scholar_helper.py, test_notion_helper.py 更新）
- [ ] 動作確認（実際の論文タイトルで python fetch.py を実行）
- [ ] 動作確認（output.txt に JSON を貼り付けて python main.py を実行し Notion DB を確認）

### 未対応

- [ ] Notion Files API の upload_pdf 関数：実際の API 仕様を検証して動作確認する
  （spec.md 記載のエンドポイント `/v1/file_uploads` が正しいかを確認する必要あり）
