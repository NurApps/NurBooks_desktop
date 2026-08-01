import os
import sqlite3
import threading

from src.core.logger import get_logger
from src.core.models import Book, Bookmark

logger = get_logger(__name__)


class LocalDatabase:
    """
    Локальный SQLite-кэш для офлайн-режима.
    Дублирует книги и прогресс чтения, чтобы каталог работал без сети.
    """

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            from src.config import DEFAULT_DATA_PATH
            db_path = os.path.join(DEFAULT_DATA_PATH, "nurbooks_local.db")
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        with self._lock:
            c = self._conn.cursor()
            c.execute(
                """CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY,
                    title TEXT DEFAULT '',
                    author TEXT DEFAULT '',
                    category TEXT DEFAULT '',
                    year INTEGER DEFAULT 0,
                    description TEXT DEFAULT '',
                    cover TEXT DEFAULT '',
                    pdf TEXT DEFAULT '',
                    file_size TEXT,
                    pages INTEGER,
                    copyright_protected INTEGER DEFAULT 0,
                    view_count INTEGER DEFAULT 0,
                    download_count INTEGER DEFAULT 0
                )"""
            )
            c.execute(
                """CREATE TABLE IF NOT EXISTS reading_progress (
                    book_id INTEGER PRIMARY KEY,
                    page INTEGER DEFAULT 0
                )"""
            )
            c.execute(
                """CREATE TABLE IF NOT EXISTS reading_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER,
                    page INTEGER DEFAULT 0,
                    duration_seconds INTEGER DEFAULT 0,
                    timestamp TEXT
                )"""
            )
            self._conn.commit()

    # ---- Books ----

    @staticmethod
    def _row_to_book(r) -> Book:
        return Book(
            id=r[0], title=r[1], author=r[2], category=r[3], year=r[4],
            description=r[5], cover=r[6], pdf=r[7], file_size=r[8], pages=r[9],
            copyright_protected=bool(r[10]), view_count=r[11], download_count=r[12],
        )

    @staticmethod
    def _book_to_row(book: Book) -> tuple:
        return (
            book.id, book.title, book.author, book.category, book.year,
            book.description, book.cover, book.pdf, book.file_size, book.pages,
            int(book.copyright_protected), book.view_count, book.download_count,
        )

    def save_books(self, books: list[Book]):
        """Полностью заменяет локальный кэш книг."""
        with self._lock:
            c = self._conn.cursor()
            c.execute("DELETE FROM books")
            c.executemany(
                """INSERT OR REPLACE INTO books
                   (id, title, author, category, year, description, cover, pdf,
                    file_size, pages, copyright_protected, view_count, download_count)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [self._book_to_row(b) for b in books],
            )
            self._conn.commit()

    def load_books(self) -> list[Book]:
        with self._lock:
            c = self._conn.cursor()
            rows = c.execute("SELECT * FROM books ORDER BY id").fetchall()
            return [self._row_to_book(r) for r in rows]

    def upsert_book(self, book: Book):
        with self._lock:
            c = self._conn.cursor()
            c.execute(
                """INSERT OR REPLACE INTO books
                   (id, title, author, category, year, description, cover, pdf,
                    file_size, pages, copyright_protected, view_count, download_count)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                self._book_to_row(book),
            )
            self._conn.commit()

    def delete_book(self, book_id: int):
        with self._lock:
            c = self._conn.cursor()
            c.execute("DELETE FROM books WHERE id = ?", (book_id,))
            c.execute("DELETE FROM reading_progress WHERE book_id = ?", (book_id,))
            self._conn.commit()

    def get_book_by_id(self, book_id: int) -> Book | None:
        with self._lock:
            c = self._conn.cursor()
            row = c.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
            return self._row_to_book(row) if row else None

    def search_books(self, query: str) -> list[Book]:
        """Поиск по названию/автору/категории (регистронезависимо, включая кириллицу)."""
        q = query.lower()
        with self._lock:
            c = self._conn.cursor()
            rows = c.execute("SELECT * FROM books ORDER BY id").fetchall()
        return [
            self._row_to_book(r)
            for r in rows
            if q in (r[1] or "").lower() or q in (r[2] or "").lower() or q in (r[3] or "").lower()
        ]

    # ---- Reading progress ----

    def save_progress(self, book_id: int, page: int):
        with self._lock:
            c = self._conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO reading_progress (book_id, page) VALUES (?, ?)",
                (book_id, page),
            )
            self._conn.commit()

    def get_progress(self, book_id: int) -> int | None:
        with self._lock:
            c = self._conn.cursor()
            row = c.execute("SELECT page FROM reading_progress WHERE book_id = ?", (book_id,)).fetchone()
            return row[0] if row else None

    def get_all_progress(self) -> dict[int, int]:
        with self._lock:
            c = self._conn.cursor()
            rows = c.execute("SELECT book_id, page FROM reading_progress").fetchall()
            return {book_id: page for book_id, page in rows}

    # ---- Reading history ----

    def add_reading_event(self, book_id: int, page: int, duration_seconds: int = 0):
        from datetime import datetime
        with self._lock:
            c = self._conn.cursor()
            c.execute(
                "INSERT INTO reading_history (book_id, page, duration_seconds, timestamp) VALUES (?, ?, ?, ?)",
                (book_id, page, duration_seconds, datetime.now().isoformat(timespec="seconds")),
            )
            self._conn.commit()

    def get_reading_history(self, limit: int = 50) -> list[dict]:
        with self._lock:
            c = self._conn.cursor()
            rows = c.execute(
                "SELECT book_id, page, duration_seconds, timestamp FROM reading_history ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"bookId": r[0], "page": r[1], "durationSeconds": r[2], "timestamp": r[3]}
            for r in rows
        ]

    def clear_reading_history(self):
        with self._lock:
            c = self._conn.cursor()
            c.execute("DELETE FROM reading_history")
            self._conn.commit()


class Database:
    """
    Хранилище с офлайн-поддержкой: Firestore через API-сервер, при недоступности — локальный SQLite.
    """

    def __init__(self, data_path=None):
        self._firebase = None
        try:
            from src.core.firebase_client import firebase_client
            self._firebase = firebase_client
        except Exception as e:
            logger.warning(f"Не удалось загрузить FirebaseClient: {e}")
        self._local = LocalDatabase()

    def _fb(self):
        if self._firebase and self._firebase.is_initialized():
            return self._firebase
        return None

    def init_db(self):
        pass

    def get_connection(self):
        return None

    def _normalize_path(self, path: str) -> str | None:
        return path

    # ---- Books ----

    def get_all_books(self) -> list[Book]:
        """Сначала Firestore (с обновлением локального кэша), при недоступности — локальный кэш."""
        fb = self._fb()
        if fb:
            books = fb.get_all_books()
            if books:
                self._local.save_books(books)
                return books
        return self._local.load_books()

    def get_book_by_id(self, book_id: int) -> Book | None:
        fb = self._fb()
        if fb:
            book = fb.get_book_by_id(book_id)
            if book:
                self._local.upsert_book(book)
                return book
        return self._local.get_book_by_id(book_id)

    def add_book(self, book: Book) -> str:
        self._local.upsert_book(book)
        fb = self._fb()
        if fb:
            return fb.add_book(book)
        return "success"

    def update_book(self, book: Book) -> bool:
        self._local.upsert_book(book)
        fb = self._fb()
        if fb:
            return fb.update_book(book)
        return True

    def update_book_file_size(self, book_id: int, file_size: str) -> bool:
        return True

    def increment_book_view_count(self, book_id: int) -> bool:
        fb = self._fb()
        if fb:
            return fb.increment_view_count(book_id)
        return False

    def increment_book_download_count(self, book_id: int) -> bool:
        fb = self._fb()
        if fb:
            return fb.increment_download_count(book_id)
        return False

    def get_book_statistics(self, book_id: int) -> dict:
        fb = self._fb()
        if fb:
            return fb.get_book_statistics(book_id)
        return {'view_count': 0, 'download_count': 0, 'view_to_download_ratio': 0}

    def delete_book(self, pdf_path: str) -> bool:
        return False

    def delete_book_by_id(self, book_id: int) -> bool:
        self._local.delete_book(book_id)
        fb = self._fb()
        if fb:
            return fb.delete_book(book_id)
        return True

    def search_books(self, query: str) -> list[Book]:
        fb = self._fb()
        if fb:
            books = fb.search_books(query)
            if books:
                self._local.save_books(books)
                return books
        return self._local.search_books(query)

    def clear_books(self):
        fb = self._fb()
        if fb:
            fb.clear_books()
        self._local.save_books([])

    # ---- Bookmarks (Firestore only) ----

    def add_bookmark(self, bookmark: Bookmark) -> bool:
        fb = self._fb()
        if fb:
            return fb.add_bookmark(bookmark)
        return False

    def delete_bookmark(self, bookmark_id) -> bool:
        fb = self._fb()
        if fb:
            return fb.delete_bookmark(bookmark_id)
        return False

    def get_bookmarks_by_book(self, book_id: int) -> list[Bookmark]:
        fb = self._fb()
        if fb:
            return fb.get_bookmarks_by_book(book_id)
        return []

    def get_all_bookmarks_with_books(self) -> list:
        fb = self._fb()
        if fb:
            return fb.get_all_bookmarks_with_books()
        return []

    # ---- Reading progress (с локальным фолбэком) ----

    def save_reading_progress(self, book_id: int, page_number: int) -> bool:
        self._local.save_progress(book_id, page_number)
        fb = self._fb()
        if fb:
            return fb.save_reading_progress(book_id, page_number)
        return True

    def get_reading_progress(self, book_id: int) -> int | None:
        fb = self._fb()
        if fb:
            result = fb.get_reading_progress(book_id)
            if result:
                self._local.save_progress(book_id, result)
                return result
        return self._local.get_progress(book_id)

    def get_all_reading_progress(self) -> dict:
        fb = self._fb()
        if fb:
            result = fb.get_all_reading_progress()
            if result:
                for book_id, page in result.items():
                    self._local.save_progress(book_id, page)
                return result
        return self._local.get_all_progress()

    def get_book_by_pdf(self, pdf_path: str) -> Book | None:
        fb = self._fb()
        if fb:
            book = fb.get_book_by_pdf(pdf_path)
            if book:
                self._local.upsert_book(book)
                return book
        for book in self._local.load_books():
            if book.pdf == pdf_path:
                return book
        return None

    # ---- Reading history (локальное хранилище + сервер) ----

    def add_reading_event(self, book_id: int, page: int, duration_seconds: int = 0) -> bool:
        self._local.add_reading_event(book_id, page, duration_seconds)
        fb = self._fb()
        if fb:
            try:
                fb.log_analytics_event("read", book_id, {
                    "page": page,
                    "durationSeconds": duration_seconds,
                })
            except Exception as e:
                logger.warning(f"Не удалось отправить событие чтения: {e}")
        return True

    def get_reading_history(self, limit: int = 50) -> list[dict]:
        fb = self._fb()
        if fb:
            try:
                history = fb.get_reading_history(limit)
                if history is not None:
                    return history
            except Exception as e:
                logger.warning(f"Не удалось получить историю с сервера: {e}")
        return self._local.get_reading_history(limit)
