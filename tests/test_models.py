from datetime import datetime

from src.core.models import Book, Bookmark, Notification, UserSettings


def test_book_to_dict():
    book = Book(id=1, title="Таухид", author="Имам", category="Акыда", year=2020, description="", cover="", pdf="x.pdf")
    d = book.to_dict()
    assert d["id"] == 1
    assert d["title"] == "Таухид"
    assert d["view_count"] == 0
    assert d["download_count"] == 0


def test_book_defaults():
    book = Book(id=2, title="T", author="A", category="C", year=0, description="", cover="", pdf="")
    assert book.copyright_protected is False
    assert book.pages is None


def test_notification_to_dict():
    n = Notification(id=1, title="t", message="m", type="info", timestamp=datetime(2026, 1, 1, 12, 0, 0))
    d = n.to_dict()
    assert d["timestamp"] == "2026-01-01T12:00:00"


def test_bookmark_to_dict():
    bm = Bookmark(id=1, book_id=10, page_number=25, timestamp="2026-01-01T12:00:00")
    d = bm.to_dict()
    assert d["book_id"] == 10
    assert d["page_number"] == 25


def test_user_settings_defaults():
    s = UserSettings(default_path="/tmp")
    assert s.theme == "light"
    assert s.language == "ru"
    assert s.auto_update is False
    assert s.enable_cloudflare_storage is False
