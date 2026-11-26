from app.storage import SQLiteVectorStore


def test_store_persists_and_ranks_vectors(tmp_path) -> None:
    database = tmp_path / "rag.sqlite3"
    store = SQLiteVectorStore(database)
    document_id = store.add_document(
        "notes.txt",
        [
            ("about networks", [1.0, 0.0]),
            ("about cooking", [0.0, 1.0]),
        ],
    )

    results = store.search([0.9, 0.1], limit=1)

    assert len(results) == 1
    assert results[0].document_id == document_id
    assert results[0].filename == "notes.txt"
    assert results[0].text == "about networks"
    assert results[0].score > 0.9
    assert SQLiteVectorStore(database).search([0.9, 0.1], limit=1)


def test_delete_document_removes_its_chunks(tmp_path) -> None:
    store = SQLiteVectorStore(tmp_path / "rag.sqlite3")
    document_id = store.add_document("one.txt", [("private note", [1.0, 0.0])])

    assert store.delete_document(document_id) is True
    assert store.search([1.0, 0.0]) == []
    assert store.delete_document(document_id) is False
