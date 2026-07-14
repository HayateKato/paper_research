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

### revise.md 対応（Notionスキーマ刷新・複数論文一括登録・DOI・--with-summary）

- [x] spec.md / CLAUDE.md を新スキーマ・新フローに更新
- [x] utils.py に sanitize_filename を追加
- [x] scholar_helper.py に DOI 取得（externalIds）を追加
- [x] fetch.py を複数タイトル対応・pdfs/命名・DOI/pdf_path保存・1件失敗時継続に変更
- [x] notion_helper.py のスキーマ刷新（Tasks/Method/Data書き込み廃止、DOI追加、create_db_entry統合）
- [x] pipeline.py を複数論文一括登録・--with-summary フラグ対応に刷新
- [x] main.py / tests/test_main.py を削除し pipeline.py に一本化
- [x] README.md を新フローに更新
- [ ] 動作確認（実際の複数論文タイトルで python pipeline.py を実行し、pdfs/・Notion DBを確認）
- [ ] 動作確認（--with-summary 付きで summary/ への貼り付け→ページ本文書き込みを確認）
- [ ] Notion DB側の実プロパティ名・型（DOI/github が url型、purpose/Data が multi_select型）が実際の DB 設定と一致しているか確認
