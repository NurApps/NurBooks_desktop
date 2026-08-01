import tempfile

from src.core.database import Database, LocalDatabase
from src.core.models import Book


def _book(book_id: int, title: str = "Книга") -> Book:
    return Book(
        id=book_id, title=title, author="Автор", category="Категория",
        year=2024, description="", cover="", pdf=f"pdfs/{book_id}.pdf",
    )


def test_local_save_load_roundtrip():
    db_path = tempfile.mktemp(suffix=".db")
    local = LocalDatabase(db_path=db_path)
    local.save_books([_book(1), _book(2, "Вторая")])
    books = local.load_books()
    assert len(books) == 2
    assert books[0].id == 1
    assert books[0].copyright_protected is False


def test_local_save_replaces_books():
    db_path = tempfile.mktemp(suffix=".db")
    local = LocalDatabase(db_path=db_path)
    local.save_books([_book(1), _book(2)])
    local.save_books([_book(3)])
    assert [b.id for b in local.load_books()] == [3]


def test_local_upsert_and_delete():
    db_path = tempfile.mktemp(suffix=".db")
    local = LocalDatabase(db_path=db_path)
    local.save_books([_book(1)])
    local.upsert_book(_book(1, "Изменённое"))
    assert local.get_book_by_id(1).title == "Изменённое"
    local.delete_book(1)
    assert local.get_book_by_id(1) is None


def test_local_search():
    db_path = tempfile.mktemp(suffix=".db")
    local = LocalDatabase(db_path=db_path)
    local.save_books([_book(1, "Таухид"), _book(2, "Фикх")])
    hits = local.search_books("таухид")
    assert [b.id for b in hits] == [1]
    assert local.search_books("нет такого") == []


def test_local_progress():
    db_path = tempfile.mktemp(suffix=".db")
    local = LocalDatabase(db_path=db_path)
    assert local.get_progress(5) is None
    local.save_progress(5, 42)
    assert local.get_progress(5) == 42
    assert local.get_all_progress() == {5: 42}


def test_database_fallback_to_local_when_no_firebase(monkeypatch):
    db_path = tempfile.mktemp(suffix=".db")
    db = Database()
    db._local = LocalDatabase(db_path=db_path)
    db._local.save_books([_book(1)])
    db._firebase = None
    assert [b.id for b in db.get_all_books()] == [1]
    assert db.get_book_by_id(1).title == "Книга"


def test_database_fallback_progress(monkeypatch):
    db_path = tempfile.mktemp(suffix=".db")
    db = Database()
    db._local = LocalDatabase(db_path=db_path)
    db._firebase = None
    assert db.save_reading_progress(7, 12) is True
    assert db.get_reading_progress(7) == 12


def test_local_reading_history_roundtrip():
    db_path = tempfile.mktemp(suffix=".db")
    local = LocalDatabase(db_path=db_path)
    assert local.get_reading_history() == []
    local.add_reading_event(5, 20, duration_seconds=120)
    local.add_reading_event(6, 1, duration_seconds=0)
    history = local.get_reading_history()
    assert len(history) == 2
    assert history[0]["bookId"] == 6
    assert history[1]["bookId"] == 5
    assert history[1]["durationSeconds"] == 120
    local.clear_reading_history()
    assert local.get_reading_history() == []


def test_database_add_reading_event_local_fallback(monkeypatch):
    db_path = tempfile.mktemp(suffix=".db")
    db = Database()
    db._local = LocalDatabase(db_path=db_path)
    db._firebase = None
    assert db.add_reading_event(9, 33, 60) is True
    assert db.get_reading_history()[0]["bookId"] == 9
