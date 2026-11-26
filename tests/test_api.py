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
        files={"file": ("notes.txt", "hello RAG".encode(), "text/plain")},
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
