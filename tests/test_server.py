import importlib
import os

from fastapi.testclient import TestClient

os.environ["NURBOOKS_API_KEY"] = ""

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


def test_technical_endpoints_exempt_from_api_key(monkeypatch):
    """Health-check и root доступны без ключа (для cron-job и мониторинга)."""
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(main, "API_KEY", "secret-key")
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


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


def test_resolve_uid_invalid_token_returns_401(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: None)
    captured = {}
    monkeypatch.setattr(fb, "get_bookmarks_by_book", lambda book_id, uid: captured.setdefault("uid", uid) or [])

    r = client.get("/bookmarks", params={"book_id": 1}, headers={"Authorization": "Bearer bad-token"})
    assert r.status_code == 401
    assert "uid" not in captured


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


# ============ Favorites ============


def test_get_favorites(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    monkeypatch.setattr(fb, "all_favorites", lambda uid: [1, 2, 3])
    r = client.get("/favorites", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert r.json() == {"favorites": [1, 2, 3]}


def test_create_favorite_scoped_by_user(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-7")
    captured = {}
    monkeypatch.setattr(fb, "add_favorite", lambda uid, bid: captured.update(uid=uid, bid=bid))

    r = client.post("/favorites", json={"bookId": 10}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert captured == {"uid": "user-7", "bid": 10}


def test_delete_favorite_scoped_by_user(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-7")
    captured = {}
    monkeypatch.setattr(fb, "remove_favorite", lambda uid, bid: captured.update(uid=uid, bid=bid))

    r = client.delete("/favorites/10", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert captured == {"uid": "user-7", "bid": 10}


# ============ Analytics history ============


def test_analytics_event_scoped_by_user(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-3")
    captured = {}
    monkeypatch.setattr(fb, "log_event", lambda et, bid, md, uid: captured.update(et=et, bid=bid, md=md, uid=uid))

    r = client.post(
        "/analytics/events",
        json={"eventType": "read", "bookId": 4, "metadata": {"page": 5}},
        headers={"Authorization": "Bearer t"},
    )
    assert r.status_code == 200
    assert captured["uid"] == "user-3"
    assert captured["et"] == "read"
    assert captured["md"] == {"page": 5}


def test_analytics_history(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-3")
    monkeypatch.setattr(fb, "get_reading_history", lambda uid: [{"bookId": 4}])
    r = client.get("/analytics/history", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert r.json() == [{"bookId": 4}]


# ============ Auth ============


def test_register_user(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-9")
    captured = {}
    monkeypatch.setattr(fb, "upsert_user", lambda uid, nick: captured.update(uid=uid, nick=nick))

    r = client.post("/auth/register", json={"nickname": "Алиса"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert captured == {"uid": "user-9", "nick": "Алиса"}


def test_register_user_requires_auth(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    r = client.post("/auth/register", json={"nickname": "Алиса"})
    assert r.status_code == 401


# ============ Wishlist ============


def test_wishlist_get_scoped_by_user(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-9")
    monkeypatch.setattr(fb, "all_wishlist", lambda uid: [5, 6])
    r = client.get("/wishlist", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert r.json() == {"wishlist": [5, 6]}


def test_wishlist_add_scoped_by_user(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-9")
    captured = {}
    monkeypatch.setattr(fb, "add_wishlist", lambda uid, bid: captured.update(uid=uid, bid=bid))
    r = client.post("/wishlist", json={"bookId": 5}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert captured == {"uid": "user-9", "bid": 5}


def test_wishlist_delete(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-9")
    captured = {}
    monkeypatch.setattr(fb, "remove_wishlist", lambda uid, bid: captured.update(uid=uid, bid=bid))
    r = client.delete("/wishlist/5", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert captured == {"uid": "user-9", "bid": 5}


# ============ Ratings ============


def test_ratings_get(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    monkeypatch.setattr(fb, "book_ratings", lambda bid, uid: {"average": 4.5, "count": 2, "userRating": 5})
    r = client.get("/books/3/ratings", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert r.json()["average"] == 4.5
    assert r.json()["userRating"] == 5


def test_ratings_put(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    captured = {}
    monkeypatch.setattr(
        fb, "upsert_rating",
        lambda uid, bid, rating, review=None, nickname=None: captured.update(uid=uid, bid=bid, rating=rating, review=review, nickname=nickname),
    )
    monkeypatch.setattr(fb, "book_ratings", lambda bid, uid: {"average": 4, "count": 1})
    r = client.put("/ratings/3", json={"bookId": 3, "rating": 4, "review": "Хорошая книга", "nickname": "ali"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert captured["rating"] == 4
    assert captured["review"] == "Хорошая книга"


def test_ratings_delete(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    captured = {}
    monkeypatch.setattr(fb, "delete_rating", lambda uid, bid: captured.update(uid=uid, bid=bid))
    r = client.delete("/ratings/3", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert captured == {"uid": "user-1", "bid": 3}


# ============ Stats ============


def test_reading_stats(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    monkeypatch.setattr(fb, "reading_stats", lambda uid, days: {"totalPages": 100, "days": []})
    r = client.get("/analytics/stats?days=14", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert r.json()["totalPages"] == 100


# ============ Leaderboard ============


def test_leaderboard(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "leaderboard", lambda days, limit: [{"nickname": "ali", "minutes": 60}])
    r = client.get("/leaderboard?days=7&limit=5")
    assert r.status_code == 200
    assert r.json()[0]["nickname"] == "ali"


# ============ Libraries ============


def test_create_library(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    monkeypatch.setattr(fb, "create_library", lambda uid, title, description, visibility, book_ids: {"id": "lib1", "ownerUid": uid, "title": title})
    r = client.post("/libraries", json={"title": "Моя библиотека", "visibility": "public", "bookIds": [1, 2]}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert r.json()["id"] == "lib1"


def test_list_libraries(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    monkeypatch.setattr(fb, "list_libraries", lambda uid: [{"id": "lib1"}])
    r = client.get("/libraries", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert r.json()[0]["id"] == "lib1"


def test_join_library_invalid_code(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    monkeypatch.setattr(fb, "get_library", lambda lib_id: {"id": "lib1"})
    monkeypatch.setattr(fb, "join_library_by_code", lambda uid, code: None)
    r = client.post("/libraries/lib1/join", json={"inviteCode": "BAD1"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 403


def test_join_library_valid_code(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    monkeypatch.setattr(fb, "get_library", lambda lib_id: {"id": "lib1"})
    monkeypatch.setattr(fb, "join_library_by_code", lambda uid, code: "lib1")
    r = client.post("/libraries/lib1/join", json={"inviteCode": "GOOD1"}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200


def test_add_book_to_library_forbidden(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    monkeypatch.setattr(fb, "add_book_to_library", lambda lid, uid, bid: False)
    r = client.post("/libraries/lib1/books", json={"bookId": 7}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 403


def test_library_rating_get(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    monkeypatch.setattr(fb, "library_rating", lambda lib_id, uid: {"average": 4.5, "count": 2, "myRating": 5})
    r = client.get("/libraries/lib1/rating", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert r.json()["average"] == 4.5
    assert r.json()["myRating"] == 5


def test_library_rating_put(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    monkeypatch.setattr(fb, "get_library", lambda lib_id: {"id": lib_id})
    monkeypatch.setattr(fb, "rate_library", lambda uid, lib_id, rating: {"average": 4.0, "count": 1, "myRating": 4})
    r = client.put("/libraries/lib1/rating", json={"rating": 4}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert r.json()["myRating"] == 4


def test_library_rating_put_not_found(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    monkeypatch.setattr(fb, "get_library", lambda lib_id: None)
    r = client.put("/libraries/lib1/rating", json={"rating": 4}, headers={"Authorization": "Bearer t"})
    assert r.status_code == 404


def test_library_rating_delete(monkeypatch):
    monkeypatch.setattr(fb, "is_ready", lambda: True)
    monkeypatch.setattr(fb, "verify_token", lambda t: "user-1")
    monkeypatch.setattr(fb, "remove_library_rating", lambda uid, lib_id: {"average": 0, "count": 0, "myRating": None})
    r = client.delete("/libraries/lib1/rating", headers={"Authorization": "Bearer t"})
    assert r.status_code == 200
    assert r.json()["myRating"] is None
