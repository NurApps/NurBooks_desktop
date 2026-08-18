from datetime import datetime, timedelta

import firebase_service as fb
import pytest
from firebase_admin import firestore as fa_firestore


class FakeIncrement:
    def __init__(self, value):
        self.value = value


class FakeSnapshot:
    def __init__(self, doc_id, data, exists=True, coll=None):
        self.id = str(doc_id)
        self._data = data
        self.exists = exists
        self._coll = coll

    def to_dict(self):
        return dict(self._data)

    @property
    def reference(self):
        return FakeDocRef(self._coll, self.id)


class FakeDocRef:
    def __init__(self, coll, doc_id=None):
        self._coll = coll
        self.id = doc_id if doc_id is not None else f"auto-{coll._counter}"

    def get(self):
        if self.id in self._coll._data:
            return FakeSnapshot(self.id, self._coll._data[self.id], coll=self._coll)
        return FakeSnapshot(self.id, {}, exists=False, coll=self._coll)

    def set(self, data, merge=False):
        if merge:
            self._coll._data.setdefault(self.id, {}).update(data)
        else:
            self._coll._data[self.id] = dict(data)

    def update(self, data):
        existing = self._coll._data.get(self.id, {})
        for k, v in data.items():
            if isinstance(v, fa_firestore.Increment) or isinstance(v, FakeIncrement):
                existing[k] = existing.get(k, 0) + v.value
            else:
                existing[k] = v
        self._coll._data[self.id] = existing

    def delete(self):
        self._coll._data.pop(self.id, None)


class FakeQuery:
    def __init__(self, coll, filters=None, order_field=None, direction=None, limit=None):
        self._coll = coll
        self._filters = filters or []
        self._order_field = order_field
        self._direction = direction
        self._limit = limit

    def where(self, field, op, value):
        return FakeQuery(self._coll, self._filters + [(field, op, value)], self._order_field, self._direction, self._limit)

    def order_by(self, field, direction="ASCENDING"):
        return FakeQuery(self._coll, self._filters, field, direction, self._limit)

    def limit(self, n):
        return FakeQuery(self._coll, self._filters, self._order_field, self._direction, n)

    def _matches(self, data):
        for field, op, value in self._filters:
            v = data.get(field)
            if op == "==":
                if v != value:
                    return False
            elif op == ">=":
                if v is None or not (v >= value):
                    return False
            elif op == "<=":
                if v is None or not (v <= value):
                    return False
        return True

    def stream(self):
        items = [(i, d) for i, d in self._coll._data.items() if self._matches(d)]
        if self._order_field:
            items.sort(key=lambda x: x[1].get(self._order_field, ""), reverse=(self._direction == "DESCENDING"))
        if self._limit is not None:
            items = items[: self._limit]
        for doc_id, data in items:
            yield FakeSnapshot(doc_id, data, coll=self._coll)


class FakeCollection:
    def __init__(self, name):
        self.name = name
        self._data = {}
        self._counter = 0

    def document(self, doc_id=None):
        if doc_id is None:
            self._counter += 1
            doc_id = f"auto-{self._counter}"
        return FakeDocRef(self, str(doc_id))

    def add(self, data):
        ref = self.document()
        ref.set(data)
        return None, ref

    def where(self, field, op, value):
        return FakeQuery(self, [(field, op, value)])

    def order_by(self, field, direction="ASCENDING"):
        return FakeQuery(self, [], field, direction)

    def stream(self):
        return FakeQuery(self).stream()

    def batch(self):
        return FakeBatch()


class FakeBatch:
    def __init__(self):
        self._ops = []

    def set(self, ref, data):
        self._ops.append((ref, dict(data)))

    def commit(self):
        for ref, data in self._ops:
            ref.set(data)
        self._ops = []


class FakeFirestore:
    def __init__(self):
        self._collections = {}

    def collection(self, name):
        return self._collections.setdefault(name, FakeCollection(name))

    def batch(self):
        return FakeBatch()


@pytest.fixture(autouse=True)
def _fake_firestore(monkeypatch):
    store = FakeFirestore()
    monkeypatch.setattr(fb, "_firestore", store)
    return store


def _now_iso(days_ago=0):
    return (datetime.now() - timedelta(days=days_ago)).isoformat()


# ---- Init / health ----


def test_verify_token_empty():
    assert fb.verify_token("") is None
    assert fb.verify_token(None) is None


def test_verify_token_valid(monkeypatch):
    monkeypatch.setattr("firebase_admin.auth.verify_id_token", lambda tok: {"uid": "user-1"})
    assert fb.verify_token("tok") == "user-1"


def test_verify_token_invalid(monkeypatch):
    monkeypatch.setattr("firebase_admin.auth.verify_id_token", lambda tok: (_ for _ in ()).throw(Exception("bad")))
    assert fb.verify_token("tok") is None


def test_is_ready_uses_firestore():
    assert fb.is_ready() is True


# ---- Books ----


def test_add_and_get_book(_fake_firestore):
    assert fb.add_book({"id": 1, "title": "A"}) == "success"
    assert fb.book_doc(1) == {"id": 1, "title": "A"}
    assert fb.book_doc(99) is None


def test_add_book_duplicate(_fake_firestore):
    fb.add_book({"id": 1, "title": "A"})
    assert fb.add_book({"id": 1, "title": "B"}) == "id_exists"


def test_update_and_delete_book(_fake_firestore):
    fb.add_book({"id": 1, "title": "A"})
    fb.update_book(1, {"id": 1, "title": "B", "viewCount": 3})
    assert fb.book_doc(1)["title"] == "B"
    fb.delete_book(1)
    assert fb.book_doc(1) is None


def test_all_books_sorted_by_id(_fake_firestore):
    fb.add_book({"id": 2, "title": "B"})
    fb.add_book({"id": 1, "title": "A"})
    assert [b["id"] for b in fb.all_books()] == [1, 2]


def test_clear_books(_fake_firestore):
    fb.add_book({"id": 1, "title": "A"})
    fb.add_book({"id": 2, "title": "B"})
    fb.clear_books()
    assert fb.all_books() == []


def test_search_books_by_title_and_author(_fake_firestore):
    fb.add_book({"id": 1, "title": "Война и мир", "author": "Толстой"})
    fb.add_book({"id": 2, "title": "Анна Каренина", "author": "Толстой"})
    fb.add_book({"id": 3, "title": "Мастер", "author": "Булгаков"})
    by_title = fb.search_books("Война")
    assert [b["id"] for b in by_title] == [1]
    by_author = fb.search_books("Толст")
    assert [b["id"] for b in by_author] == [1, 2]


def test_search_books_no_duplicates(_fake_firestore):
    fb.add_book({"id": 1, "title": "Книга X", "author": "Книга X"})
    assert len(fb.search_books("Книга X")) == 1


def test_get_book_by_pdf(_fake_firestore):
    fb.add_book({"id": 1, "pdf": "/files/1.pdf", "title": "A"})
    assert fb.get_book_by_pdf("/files/1.pdf")["id"] == 1
    assert fb.get_book_by_pdf("/files/none.pdf") is None


def test_increment_view_and_download(_fake_firestore):
    fb.add_book({"id": 1, "title": "A"})
    fb.increment_view(1)
    fb.increment_view(1)
    fb.increment_download(1)
    assert fb.book_doc(1)["viewCount"] == 2
    assert fb.book_doc(1)["downloadCount"] == 1


def test_book_statistics(_fake_firestore):
    fb.add_book({"id": 1, "title": "A", "viewCount": 10, "downloadCount": 2})
    stats = fb.book_statistics(1)
    assert stats == {"view_count": 10, "download_count": 2, "view_to_download_ratio": 0.2}
    assert fb.book_statistics(999) == {"view_count": 0, "download_count": 0, "view_to_download_ratio": 0}


def test_book_statistics_zero_views(_fake_firestore):
    fb.add_book({"id": 1, "title": "A", "downloadCount": 5})
    assert fb.book_statistics(1)["view_to_download_ratio"] == 0


# ---- Authors ----


def test_authors_crud(_fake_firestore):
    assert fb.add_author({"id": 1, "name": "Толстой"}) == "success"
    assert fb.add_author({"id": 1, "name": "Другой"}) == "id_exists"
    fb.save_authors([{"id": 1, "name": "Толстой"}, {"id": 2, "name": "Пушкин"}])
    assert [a["id"] for a in fb.all_authors()] == [1, 2]


# ---- Bookmarks ----


def test_add_bookmark_generates_id_and_defaults(_fake_firestore):
    bm = fb.add_bookmark({"bookId": 5, "page": 12})
    assert bm["id"]
    assert bm["userId"] == "public"
    assert bm["bookId"] == 5
    assert bm["page"] == 12


def test_get_bookmarks_filters_by_uid(_fake_firestore):
    fb.add_bookmark({"bookId": 5, "page": 1, "userId": "u1"})
    fb.add_bookmark({"bookId": 5, "page": 2, "userId": "u2"})
    fb.add_bookmark({"bookId": 5, "page": 3, "userId": "u1"})
    assert [b["page"] for b in fb.get_bookmarks_by_book(5, "u1")] == [1, 3]
    assert [b["page"] for b in fb.get_bookmarks_by_book(5, "u2")] == [2]
    assert [b["page"] for b in fb.get_bookmarks_by_book(5, "public")] == []


def test_delete_bookmark_checks_owner(_fake_firestore):
    bm = fb.add_bookmark({"bookId": 5, "page": 1, "userId": "u1"})
    fb.delete_bookmark(bm["id"], "u2")
    assert fb.get_bookmarks_by_book(5, "u1") != []
    fb.delete_bookmark(bm["id"], "u1")
    assert fb.get_bookmarks_by_book(5, "u1") == []


def test_all_bookmarks_with_books(_fake_firestore):
    fb.add_book({"id": 5, "title": "Книга"})
    fb.add_bookmark({"bookId": 5, "page": 1, "userId": "u1"})
    fb.add_bookmark({"bookId": 5, "page": 1, "userId": "u2"})
    items = fb.all_bookmarks_with_books("u1")
    assert len(items) == 1
    assert items[0]["book"]["title"] == "Книга"


# ---- Favorites ----


def test_favorites_roundtrip(_fake_firestore):
    fb.add_favorite("u1", 10)
    fb.add_favorite("u1", 20)
    fb.add_favorite("u2", 30)
    assert fb.all_favorites("u1") == [10, 20]
    fb.remove_favorite("u1", 10)
    assert fb.all_favorites("u1") == [20]
    fb.remove_favorite("u1", 10)  # повторное удаление безопасно


def test_remove_favorite_checks_owner(_fake_firestore):
    fb.add_favorite("u1", 10)
    fb.remove_favorite("u2", 10)
    assert fb.all_favorites("u1") == [10]


# ---- Wishlist ----


def test_wishlist_roundtrip(_fake_firestore):
    fb.add_wishlist("u1", 10)
    fb.add_wishlist("u1", 20)
    assert fb.all_wishlist("u1") == [10, 20]
    fb.remove_wishlist("u1", 10)
    assert fb.all_wishlist("u1") == [20]


# ---- Ratings ----


def test_upsert_rating_clamps_and_merges(_fake_firestore):
    fb.upsert_rating("u1", 3, 7)  # > 5 -> 5
    fb.upsert_rating("u1", 3, 0)  # < 1 -> 1
    assert fb.book_ratings(3, "u1")["userRating"] == 1
    fb.upsert_rating("u1", 3, 4, review="   Отлично  ", nickname="Алиса")
    data = fb.book_ratings(3, "u1")
    assert data["userRating"] == 4
    assert data["reviews"][0]["review"] == "Отлично"
    assert data["reviews"][0]["nickname"] == "Алиса"


def test_book_ratings_aggregate(_fake_firestore):
    fb.upsert_rating("u1", 3, 5)
    fb.upsert_rating("u2", 3, 3)
    fb.upsert_rating("u3", 3, 5)
    data = fb.book_ratings(3, "u2")
    assert data["count"] == 3
    assert data["average"] == round(13 / 3, 2)
    assert data["userRating"] == 3
    assert data["distribution"] == {"1": 0, "2": 0, "3": 1, "4": 0, "5": 2}
    assert fb.book_ratings(99).get("userRating") is None


def test_delete_rating_checks_owner(_fake_firestore):
    fb.upsert_rating("u1", 3, 5)
    fb.delete_rating("u2", 3)
    assert fb.book_ratings(3)["count"] == 1
    fb.delete_rating("u1", 3)
    assert fb.book_ratings(3)["count"] == 0


# ---- Users ----


def test_upsert_user(_fake_firestore):
    fb.upsert_user("u1", "Алиса")
    doc = _fake_firestore.collection("users").document("u1").get()
    assert doc.to_dict()["nickname"] == "Алиса"


# ---- Reading progress ----


def test_reading_progress_roundtrip(_fake_firestore):
    fb.save_reading_progress(3, 42, "u1")
    assert fb.get_reading_progress(3, "u1") == 42
    assert fb.get_reading_progress(3, "u2") is None


def test_reading_progress_legacy_fallback(_fake_firestore):
    _fake_firestore.collection("reading_progress").document("5").set({"bookId": 5, "page": 99})
    assert fb.get_reading_progress(5, "u1") == 99


def test_all_reading_progress_filters_uid(_fake_firestore):
    fb.save_reading_progress(3, 42, "u1")
    fb.save_reading_progress(4, 10, "u2")
    assert fb.all_reading_progress("u1") == {3: 42}


# ---- Analytics events ----


def test_log_event_stores_event(_fake_firestore):
    fb.log_event("read", 5, {"page": 10}, "u1")
    docs = list(_fake_firestore.collection("analytics_events").stream())
    assert len(docs) == 1
    assert docs[0].to_dict()["eventType"] == "read"
    assert docs[0].to_dict()["bookId"] == 5


def test_get_reading_history(_fake_firestore):
    fb.add_book({"id": 5, "title": "Книга"})
    fb.log_event("read", 5, {"page": 7, "durationSeconds": 120}, "u1")
    fb.log_event("read_open", 5, {"page": 1}, "u1")
    fb.log_event("view", 5, {}, "u1")  # не попадёт в историю чтения
    fb.log_event("read", 6, {"page": 1}, "u2")  # другой пользователь
    history = fb.get_reading_history("u1")
    assert len(history) == 2
    assert all(h["book"]["id"] == 5 for h in history)
    assert history[0]["eventType"] == "read"


def test_get_book_analytics(_fake_firestore):
    fb.log_event("view", 5)
    fb.log_event("view", 5)
    fb.log_event("download", 5)
    assert fb.get_book_analytics(5) == {"views": 2, "downloads": 1}


# ---- Reading stats ----


def test_reading_stats(_fake_firestore):
    fb.log_event("read", 5, {"page": 10, "durationSeconds": 600}, "u1")
    fb.log_event("read", 5, {"page": 5, "durationSeconds": 300}, "u1")
    fb.log_event("read", 6, {"page": 3, "durationSeconds": 120}, "u1")
    fb.log_event("read", 5, {"page": 1}, "u2")
    stats = fb.reading_stats("u1", days=30)
    assert stats["totalPages"] == 18
    assert stats["totalMinutes"] == 17
    assert stats["totalSessions"] == 3
    assert stats["booksRead"] == 2
    assert len(stats["days"]) == 30


def test_reading_stats_ignores_old_events(_fake_firestore):
    old = (datetime.now() - timedelta(days=60)).isoformat()
    _fake_firestore.collection("analytics_events").add({
        "eventType": "read", "bookId": 5, "userId": "u1", "page": 9,
        "timestamp": old, "durationSeconds": 60,
    })
    assert fb.reading_stats("u1", days=30)["totalSessions"] == 0


def test_ts_to_date():
    assert fb._ts_to_date("2026-01-02T10:00:00") == "2026-01-02"
    assert fb._ts_to_date("2026-01-02T10:00:00Z") == "2026-01-02"
    assert fb._ts_to_date("bad") is None
    assert fb._ts_to_date(None) is None


# ---- Leaderboard ----


def test_leaderboard(_fake_firestore):
    fb.upsert_user("u1", "Алиса")
    fb.log_event("read", 5, {"durationSeconds": 1200, "page": 10}, "u1")
    fb.log_event("read", 5, {"durationSeconds": 600, "page": 5}, "u2")
    fb.log_event("read", 5, {"durationSeconds": 99999, "page": 1}, "public")
    rows = fb.leaderboard(days=7, limit=10)
    assert rows[0]["uid"] == "u1"
    assert rows[0]["nickname"] == "Алиса"
    assert rows[0]["minutes"] == 20
    assert "public" not in [r["uid"] for r in rows]


def test_leaderboard_default_nickname(_fake_firestore):
    fb.log_event("read", 5, {"durationSeconds": 600, "page": 1}, "some-user")
    rows = fb.leaderboard(days=7, limit=10)
    assert rows[0]["nickname"] == fb._default_nickname("some-user")


def test_default_nickname():
    assert fb._default_nickname("abc123").startswith("Читатель-")


# ---- Libraries ----


def test_create_library(_fake_firestore):
    lib = fb.create_library("u1", "  Моя библиотека  ", "Описание", "public", [1, 2])
    assert lib["id"]
    assert lib["ownerUid"] == "u1"
    assert lib["title"] == "Моя библиотека"
    assert lib["visibility"] == "public"
    assert lib["bookCount"] == 2
    assert lib["memberCount"] == 1
    assert lib["inviteCode"]


def test_create_library_defaults(_fake_firestore):
    lib = fb.create_library("u1", "", "", "secret", None)
    assert lib["title"] == "Библиотека"
    assert lib["visibility"] == "public"


def test_get_and_list_libraries(_fake_firestore):
    lib = fb.create_library("u1", "Моя", "", "private", [])
    assert fb.get_library(lib["id"])["title"] == "Моя"
    assert fb.get_library("nope") is None
    # private библиотека чужого пользователя не видна
    assert fb.list_libraries("u2") == []
    assert fb.list_libraries("u1")[0]["id"] == lib["id"]


def test_list_libraries_public(_fake_firestore):
    lib = fb.create_library("u1", "Публичная", "", "public", [])
    assert fb.list_libraries("u2")[0]["id"] == lib["id"]


def test_update_library_owner_only(_fake_firestore):
    lib = fb.create_library("u1", "Моя", "", "public", [1])
    assert fb.update_library(lib["id"], "u2", {"title": "Чужой"}) is False
    assert fb.update_library(lib["id"], "u1", {"title": "Новый", "visibility": "private", "bookIds": [7]}) is True
    updated = fb.get_library(lib["id"])
    assert updated["title"] == "Новый"
    assert updated["visibility"] == "private"
    assert updated["bookIds"] == [7]


def test_delete_library_owner_only(_fake_firestore):
    lib = fb.create_library("u1", "Моя", "", "public", [])
    assert fb.delete_library(lib["id"], "u2") is False
    assert fb.delete_library(lib["id"], "u1") is True
    assert fb.get_library(lib["id"]) is None


def test_add_remove_book_library_owner_only(_fake_firestore):
    lib = fb.create_library("u1", "Моя", "", "public", [1])
    assert fb.add_book_to_library(lib["id"], "u2", 5) is False
    assert fb.add_book_to_library(lib["id"], "u1", 5) is True
    assert fb.add_book_to_library(lib["id"], "u1", 5) is True  # идемпотентно
    assert fb.get_library(lib["id"])["bookIds"] == [1, 5]
    assert fb.remove_book_from_library(lib["id"], "u1", 1) is True
    assert fb.get_library(lib["id"])["bookIds"] == [5]


def test_join_library_by_code(_fake_firestore):
    lib = fb.create_library("u1", "Моя", "", "private", [])
    code = lib["inviteCode"]
    assert fb.join_library_by_code("u2", code.lower()) == lib["id"]  # case-insensitive
    assert "u2" in fb.get_library(lib["id"])["memberUids"]
    # владелец не добавляет себя в участники
    assert fb.join_library_by_code("u1", code) == lib["id"]
    assert fb.get_library(lib["id"])["memberCount"] == 2
    assert fb.join_library_by_code("u3", "XXXXXX") is None


def test_join_library_second_time_no_duplicate(_fake_firestore):
    lib = fb.create_library("u1", "Моя", "", "private", [])
    fb.join_library_by_code("u2", lib["inviteCode"])
    fb.join_library_by_code("u2", lib["inviteCode"])
    assert len(fb.get_library(lib["id"])["memberUids"]) == 1


def test_library_rating_flow(_fake_firestore):
    lib = fb.create_library("u1", "Моя", "", "public", [])
    r1 = fb.rate_library("u2", lib["id"], 5)
    assert r1["average"] == 5.0
    assert r1["myRating"] == 5
    fb.rate_library("u2", lib["id"], 3)
    r2 = fb.library_rating(lib["id"], "u2")
    assert r2["average"] == 3.0
    assert r2["count"] == 1
    fb.remove_library_rating("u2", lib["id"])
    assert fb.library_rating(lib["id"], "u2")["count"] == 0
    assert fb.rate_library("u3", "nope", 5) == {}


def test_library_rating_distribution(_fake_firestore):
    lib = fb.create_library("u1", "Моя", "", "public", [])
    fb.rate_library("u2", lib["id"], 5)
    fb.rate_library("u3", lib["id"], 1)
    fb.rate_library("u4", lib["id"], 5)
    r = fb.library_rating(lib["id"])
    assert r["count"] == 3
    assert r["average"] == round(11 / 3, 2)
    assert r["distribution"] == {1: 1, 2: 0, 3: 0, 4: 0, 5: 2}
