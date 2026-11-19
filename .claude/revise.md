修正点
- notebooklmの要約を入れる処理はいらない（notebooklmの要約を入れるかどうかパラメータ化する？）
- 取得したpdfに論文の名前をつける
- doiを取得してnotionに登録する
- 複数論文を一気に追加できるようにする

notionのdbスキーマは以下の通り
- title(page)
- purpose(multi select, 空白にする)
- PDF(pdf)
- DOI(link)
- Data(multi select)
- Authors(multi select)
- year(number)
- venue(text)
- bibtex(text)
- github(link, 空白する)

検証方法

- pytest tests/ で全テストが通ることを確認。
- 実際に .env を設定した上で python pipeline.py "適当な論文タイトル1" "適当な論文タイトル2" を実行し、以下を確認:
  - scholar_data.json に doi/pdf_path が保存される
  - pdfs/ 配下にタイトル名のPDFが2件作成される
  - Notion DBに新スキーマ（purpose/Data/github空欄、DOI設定済み）でエントリが2件作成され、Statusが「完了」になる
  - --with-summary を付けて実行した場合、summary/ 配下にファイルが生成され、入力後Enterでページ本文が書き込まれ、Statusが「完了」になることを確認
  - 存在しない架空タイトルを含めて実行し、そのタイトルのみスキップされ他が正常処理されることを確認

- 1件パターンもやる