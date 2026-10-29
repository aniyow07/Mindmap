import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTOMAP_EMBEDDER", "tfidf")  # keep tests fast and offline
    from server import app

    return TestClient(app)


def test_health(client):
    assert client.get("/api/health").json() == {"ok": True}


def test_serves_viewer(client):
    res = client.get("/")
    assert res.status_code == 200 and "AutoMap" in res.text


def test_maps_a_pdf(client, paper):
    res = client.post("/api/map", files={"file": ("paper.pdf", paper.read_bytes(), "application/pdf")})
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "A Tale of Two Topics"
    assert body["stats"]["file"] == "paper.pdf"


def test_rejects_non_pdf(client):
    res = client.post("/api/map", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert res.status_code == 415
