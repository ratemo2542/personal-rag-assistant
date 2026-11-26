from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_preview_accepts_utf8_text() -> None:
    response = client.post(
        "/documents/preview",
        files={"file": ("notes.txt", b"hello RAG", "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "hello RAG"


def test_preview_rejects_unsupported_extension() -> None:
    response = client.post(
        "/documents/preview",
        files={"file": ("payload.exe", b"not executable", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_preview_rejects_empty_file() -> None:
    response = client.post(
        "/documents/preview",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400


def test_ingest_and_search_use_local_store(monkeypatch, tmp_path) -> None:
    from app import main

    class FakeEmbedder:
        def embed(self, texts):
            return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(main, "embedder", FakeEmbedder())
    monkeypatch.setattr(main, "DATABASE_PATH", str(tmp_path / "test.sqlite3"))

    ingest = client.post(
        "/documents/ingest",
        files={"file": ("notes.txt", b"Computer networks connect devices.", "text/plain")},
    )
    assert ingest.status_code == 200
    assert ingest.json()["chunks"] == 1

    search = client.post("/search", json={"query": "computer networks"})
    assert search.status_code == 200
    assert search.json()["results"][0]["filename"] == "notes.txt"
    assert "connect devices" in search.json()["results"][0]["text"]


def test_search_validates_query_length() -> None:
    response = client.post("/search", json={"query": "x"})
    assert response.status_code == 422
