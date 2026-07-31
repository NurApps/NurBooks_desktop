import importlib

from fastapi.testclient import TestClient

main = importlib.import_module("main")
import firebase_service as fb

client = TestClient(main.app)


def test_health_ok(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_error(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: False)
    monkeypatch.setattr(fb, "init_error", lambda: "no creds")
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "error"


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["name"] == "NurBooks API"


def test_books_empty(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "all_books", lambda: [])
    r = client.get("/books")
    assert r.status_code == 200
    assert r.json() == []


def test_books_list(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "all_books", lambda: [{"id": 1, "title": "Таухид"}])
    r = client.get("/books")
    assert r.status_code == 200
    assert r.json()[0]["title"] == "Таухид"


def test_firebase_unavailable_returns_503(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: False)
    r = client.get("/books")
    assert r.status_code == 503


def test_api_key_rejected(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(main, "API_KEY", "secret-key")
    r = client.get("/books", params={"api_key": "wrong"})
    assert r.status_code == 403


def test_api_key_accepted(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(main, "API_KEY", "secret-key")
    monkeypatch.setattr(fb, "all_books", lambda: [])
    r = client.get("/books", params={"api_key": "secret-key"})
    assert r.status_code == 200


def test_api_key_accepted_via_header(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(main, "API_KEY", "secret-key")
    monkeypatch.setattr(fb, "all_books", lambda: [])
    r = client.get("/books", headers={"X-API-Key": "secret-key"})
    assert r.status_code == 200


def test_api_key_rejected_via_header(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(main, "API_KEY", "secret-key")
    r = client.get("/books", headers={"X-API-Key": "wrong"})
    assert r.status_code == 403


def test_create_book_conflict(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "add_book", lambda d: "id_exists")
    payload = {"id": 1, "title": "T", "author": "A", "category": "C", "pdf": "x.pdf"}
    r = client.post("/books", json=payload)
    assert r.status_code == 409


def test_create_book_success(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "add_book", lambda d: "success")
    payload = {"id": 2, "title": "T", "author": "A", "category": "C", "pdf": "x.pdf"}
    r = client.post("/books", json=payload)
    assert r.status_code == 200


def test_get_book_not_found(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "book_doc", lambda book_id: None)
    r = client.get("/books/999")
    assert r.status_code == 404


def test_get_book_found(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "book_doc", lambda book_id: {"id": book_id, "title": "T"})
    r = client.get("/books/5")
    assert r.status_code == 200
    assert r.json()["id"] == 5


def test_resolve_uid_public_without_token(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: None)
    monkeypatch.setattr(fb, "get_bookmarks_by_book", lambda book_id, uid: [])
    r = client.get("/bookmarks", params={"book_id": 1})
    assert r.status_code == 200


def test_resolve_uid_from_valid_token(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-123")
    captured = {}
    monkeypatch.setattr(fb, "get_bookmarks_by_book", lambda book_id, uid: captured.setdefault("uid", uid) or [])

    r = client.get("/bookmarks", params={"book_id": 1}, headers={"Authorization": "Bearer valid-token"})
    assert r.status_code == 200
    assert captured["uid"] == "user-123"


def test_resolve_uid_invalid_token_falls_back_to_public(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: None)
    captured = {}
    monkeypatch.setattr(fb, "get_bookmarks_by_book", lambda book_id, uid: captured.setdefault("uid", uid) or [])

    client.get("/bookmarks", params={"book_id": 1}, headers={"Authorization": "Bearer bad-token"})
    assert captured["uid"] == "public"


def test_create_bookmark_stores_user_id(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-42")
    captured = {}
    monkeypatch.setattr(fb, "add_bookmark", lambda d: captured.setdefault("data", d) or d)

    r = client.post(
        "/bookmarks",
        json={"bookId": 1, "page": 5},
        headers={"Authorization": "Bearer t"},
    )
    assert r.status_code == 200
    assert captured["data"]["userId"] == "user-42"


def test_reading_progress_scoped_by_user(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-9")
    captured = {}
    monkeypatch.setattr(fb, "save_reading_progress", lambda bid, page, uid: captured.update(bid=bid, page=page, uid=uid))

    r = client.put(
        "/reading-progress/3",
        json={"bookId": 3, "page": 50},
        headers={"Authorization": "Bearer t"},
    )
    assert r.status_code == 200
    assert captured == {"bid": 3, "page": 50, "uid": "user-9"}
