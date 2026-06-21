import sqlite3
import os
from typing import List, Optional
from src.core.models import Book, Bookmark
from src.config import DEFAULT_DATA_PATH
from src.core.logger import get_logger
from src.core.analytics import Analytics

logger = get_logger(__name__)


class Database:
    def __init__(self, data_path=None):
        if data_path is None:
            from src.config import DEFAULT_DATA_PATH
            self.data_path = DEFAULT_DATA_PATH
        else:
            self.data_path = data_path
        self.db_path = os.path.join(self.data_path, "books.db")
        self.analytics = Analytics()  # Добавляем объект аналитики
        self.init_db()

    def init_db(self):
        """Инициализирует базу данных и создает таблицы, если они не существуют"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Создаем таблицу для книг с ID, который не является AUTOINCREMENT
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                category TEXT NOT NULL,
                year INTEGER,
                description TEXT,
                cover TEXT,
                pdf TEXT NOT NULL UNIQUE,
                file_size TEXT,
                pages INTEGER,
                copyright_protected INTEGER NOT NULL DEFAULT 0,
                view_count INTEGER NOT NULL DEFAULT 0,
                download_count INTEGER NOT NULL DEFAULT 0
            )
        ''')
        cursor.execute("PRAGMA table_info(books)")
        columns = [row[1] for row in cursor.fetchall()]
        if "copyright_protected" not in columns:
            cursor.execute(
                "ALTER TABLE books ADD COLUMN copyright_protected INTEGER NOT NULL DEFAULT 0"
            )
        if "view_count" not in columns:
            cursor.execute(
                "ALTER TABLE books ADD COLUMN view_count INTEGER NOT NULL DEFAULT 0"
            )
        if "download_count" not in columns:
            cursor.execute(
                "ALTER TABLE books ADD COLUMN download_count INTEGER NOT NULL DEFAULT 0"
            )
        
        # Создаем таблицу для закладок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (book_id) REFERENCES books (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def get_connection(self):
        """Возвращает соединение с базой данных"""
        return sqlite3.connect(self.db_path)

    def _normalize_path(self, path: str) -> Optional[str]:
        """Преобразует путь в нормализованный формат (URL или относительный путь)"""
        if not path:
            return None

        # Если это URL, возвращаем как есть (уже должен быть в raw формате)
        if path.startswith(('http://', 'https://')):
            return path

        # Для локальных путей сохраняем относительный формат
        filename = os.path.basename(path)

        # Если это PDF или обложка, сохраняем относительный путь от корня программы
        if "pdfs" in path.lower() or path.endswith('.pdf'):
            return f"pdfs/{filename}"
        if "thumbnails" in path.lower() or "covers" in path.lower():
            return f"data/thumbnails/{filename}"

        # Возвращаем как есть, нормализуя слеши
        return path.replace('\\', '/')

    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        """Получает книгу по ее ID."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM books WHERE id=?", (book_id,))
            row = cursor.fetchone()

            if row:
                book = Book(
                    id=row[0], title=row[1], author=row[2], category=row[3], year=row[4],
                    description=row[5], cover=row[6], pdf=row[7], file_size=row[8], pages=row[9],
                    copyright_protected=bool(row[10]) if len(row) > 10 else False,
                    view_count=int(row[11]) if len(row) > 11 else 0,
                    download_count=int(row[12]) if len(row) > 12 else 0
                )
                conn.close()
                return book
            else:
                conn.close()
                return None
        except Exception as e:
            logger.error(f"Ошибка получения книги по ID: {e}", exc_info=True)
            conn.close()
            return None

    def add_book(self, book: Book) -> str:
        """
        Добавляет книгу в базу данных.
        Возвращает "success", "id_exists" или "pdf_exists".
        """
        try:
            if self.get_book_by_id(book.id):
                return "id_exists"

            conn = self.get_connection()
            cursor = conn.cursor()

            cover_path = self._normalize_path(book.cover)
            pdf_path = self._normalize_path(book.pdf)

            cursor.execute('''
                INSERT INTO books (id, title, author, category, year, description, cover, pdf, file_size, pages, copyright_protected, view_count, download_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (book.id, book.title, book.author, book.category, book.year, book.description,
                  cover_path, pdf_path, book.file_size, book.pages, int(bool(book.copyright_protected)),
                  int(getattr(book, "view_count", 0)), int(getattr(book, "download_count", 0))))

            conn.commit()
            conn.close()
            self.analytics.track_book_added(book)  # Отслеживаем добавление книги
            return "success"
        except sqlite3.IntegrityError:
            conn.close()
            return "pdf_exists"
        except Exception as e:
            logger.error(f"Ошибка добавления книги в базу данных: {e}", exc_info=True)
            conn.close()
            return "error"

    def update_book(self, book: Book) -> bool:
        """Обновляет информацию о книге в базе данных"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Проверяем, не существует ли уже PDF у другой книги
            cursor.execute("SELECT id FROM books WHERE pdf=? AND id!=?", (book.pdf, book.id))
            existing = cursor.fetchone()
            if existing:
                conn.close()
                logger.warning(f"PDF '{book.pdf}' уже привязан к другой книге (ID: {existing[0]})")
                return False

            cover_path = self._normalize_path(book.cover)
            pdf_path = self._normalize_path(book.pdf)

            cursor.execute('''
                UPDATE books SET title=?, author=?, category=?, year=?, description=?,
                cover=?, pdf=?, file_size=?, pages=?, copyright_protected=?, view_count=?, download_count=? WHERE id=?
            ''', (book.title, book.author, book.category, book.year, book.description,
                  cover_path, pdf_path, book.file_size, book.pages, int(bool(book.copyright_protected)),
                  int(getattr(book, "view_count", 0)), int(getattr(book, "download_count", 0)), book.id))

            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()
            if affected_rows > 0:
                self.analytics.track_book_updated(book) # Отслеживаем обновление книги
            return affected_rows > 0
        except Exception as e:
            logger.error(f"Ошибка обновления книги в базе данных: {e}", exc_info=True)
            conn.close()
            return False

    def update_book_file_size(self, book_id: int, file_size: str) -> bool:
        """Обновляет размер файла книги в базе данных"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE books SET file_size=? WHERE id=?
            ''', (file_size, book_id))
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()
            return affected_rows > 0
        except Exception as e:
            logger.error(f"Ошибка обновления размера файла книги в базе данных: {e}", exc_info=True)
            conn.close()
            return False

    def increment_book_view_count(self, book_id: int) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE books SET view_count = view_count + 1 WHERE id=?", (book_id,))
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()

            # Записываем в аналитику
            if self.analytics:
                self.analytics.log_view(book_id)
            return affected_rows > 0
        except Exception as e:
            logger.error(f"Ошибка увеличения счетчика просмотров: {e}", exc_info=True)
            conn.close()
            return False

    def increment_book_download_count(self, book_id: int) -> bool:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE books SET download_count = download_count + 1 WHERE id=?", (book_id,))
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()

            # Записываем в аналитику
            if self.analytics:
                self.analytics.log_download(book_id)
            return affected_rows > 0
        except Exception as e:
            logger.error(f"Ошибка увеличения счетчика скачиваний: {e}", exc_info=True)
            conn.close()
            return False

    def get_book_statistics(self, book_id: int) -> dict:
        """Получает статистику по книге из аналитики и базы данных"""
        db_view_count = 0
        db_download_count = 0
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT view_count, download_count FROM books WHERE id=?", (book_id,))
            row = cursor.fetchone()
            if row:
                db_view_count = row[0] or 0
                db_download_count = row[1] or 0
                conn.close()
        except Exception:
            pass

        analytics_stats = {}
        if self.analytics:
            analytics_stats = self.analytics.get_book_statistics(book_id)
        return {
            'view_count': db_view_count + analytics_stats.get('views', 0),
            'download_count': db_download_count + analytics_stats.get('downloads', 0),
            'view_to_download_ratio': analytics_stats.get('view_to_download_ratio', 0),
        }

    def delete_book(self, pdf_path: str) -> bool:
        """Удаляет книгу из базы данных по пути к PDF"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем информацию о книге перед удалением для аналитики
            cursor.execute("SELECT * FROM books WHERE pdf=?", (pdf_path,))
            book_row = cursor.fetchone()

            cursor.execute("DELETE FROM books WHERE pdf=?", (pdf_path,))
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()

            if affected_rows > 0 and book_row:
                # Преобразуем строку в объект Book для аналитики
                book_to_delete = Book(
                    id=book_row[0], title=book_row[1], author=book_row[2], category=book_row[3], year=book_row[4],
                    description=book_row[5], cover=book_row[6], pdf=book_row[7], file_size=book_row[8], pages=book_row[9],
                    copyright_protected=bool(book_row[10]) if len(book_row) > 10 else False,
                    view_count=int(book_row[11]) if len(book_row) > 11 else 0,
                    download_count=int(book_row[12]) if len(book_row) > 12 else 0
                )
                self.analytics.track_book_deleted(book_to_delete) # Отслеживаем удаление книги
            return affected_rows > 0
        except Exception as e:
            logger.error(f"Ошибка удаления книги из базы данных: {e}", exc_info=True)
            conn.close()
            return False

    def delete_book_by_id(self, book_id: int) -> bool:
        """Удаляет книгу из базы данных по ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем информацию о книге перед удалением для аналитики
            cursor.execute("SELECT * FROM books WHERE id=?", (book_id,))
            book_row = cursor.fetchone()
            
            cursor.execute("DELETE FROM books WHERE id=?", (book_id,))
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()

            if affected_rows > 0 and book_row:
                 # Преобразуем строку в объект Book для аналитики
                book_to_delete = Book(
                    id=book_row[0], title=book_row[1], author=book_row[2], category=book_row[3], year=book_row[4],
                    description=book_row[5], cover=book_row[6], pdf=book_row[7], file_size=book_row[8], pages=book_row[9],
                    copyright_protected=bool(book_row[10]) if len(book_row) > 10 else False,
                    view_count=int(book_row[11]) if len(book_row) > 11 else 0,
                    download_count=int(book_row[12]) if len(book_row) > 12 else 0
                )
                self.analytics.track_book_deleted(book_to_delete) # Отслеживаем удаление книги
            return affected_rows > 0
        except Exception as e:
            logger.error(f"Ошибка удаления книги из базы данных: {e}", exc_info=True)
            conn.close()
            return False

    def add_bookmark(self, bookmark: Bookmark) -> bool:
        """Добавляет закладку в базу данных"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO bookmarks (book_id, page_number, timestamp)
                VALUES (?, ?, ?)
            ''', (bookmark.book_id, bookmark.page_number, bookmark.timestamp))
            conn.commit()
            affected = cursor.rowcount > 0
            bookmark.id = cursor.lastrowid
            conn.close()
            if affected:
                self.analytics.track_bookmark_added(bookmark) # Отслеживаем добавление закладки
            return affected
        except Exception as e:
            logger.error(f"Ошибка добавления закладки в базу данных: {e}", exc_info=True)
            conn.close()
            return False

    def delete_bookmark(self, bookmark_id: int) -> bool:
        """Удаляет закладку из базы данных по ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем информацию о закладке перед удалением для аналитики
            cursor.execute("SELECT * FROM bookmarks WHERE id=?", (bookmark_id,))
            bookmark_row = cursor.fetchone()

            cursor.execute("DELETE FROM bookmarks WHERE id=?", (bookmark_id,))
            
            conn.commit()
            affected = cursor.rowcount > 0
            conn.close()

            if affected and bookmark_row:
                # Преобразуем строку в объект Bookmark для аналитики
                bookmark_to_delete = Bookmark(
                    id=bookmark_row[0],
                    book_id=bookmark_row[1],
                    page_number=bookmark_row[2],
                    timestamp=bookmark_row[3]
                )
                self.analytics.track_bookmark_deleted(bookmark_to_delete) # Отслеживаем удаление закладки
            return affected
        except Exception as e:
            logger.error(f"Ошибка удаления закладки из базы данных: {e}", exc_info=True)
            conn.close()
            return False

    def get_bookmarks_by_book(self, book_id: int) -> List[Bookmark]:
        """Получает все закладки для конкретной книги"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM bookmarks WHERE book_id=? ORDER BY page_number", (book_id,))
            rows = cursor.fetchall()
            
            conn.close()
            
            bookmarks = []
            for row in rows:
                bookmark = Bookmark(
                    id=row[0],
                    book_id=row[1],
                    page_number=row[2],
                    timestamp=row[3]
                )
                bookmarks.append(bookmark)
            return bookmarks
        except Exception as e:
            logger.error(f"Ошибка получения закладок из базы данных: {e}", exc_info=True)
            conn.close()
            return []

    def get_all_bookmarks_with_books(self) -> List[tuple]:
        """Получает все закладки с информацией о книгах"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT b.id, b.book_id, b.page_number, b.timestamp,
                       bk.id, bk.title, bk.author, bk.category, bk.year,
                       bk.description, bk.cover, bk.pdf, bk.file_size, bk.pages, bk.copyright_protected, bk.view_count, bk.download_count
                FROM bookmarks b
                JOIN books bk ON b.book_id = bk.id
                ORDER BY b.timestamp DESC
            ''')
            rows = cursor.fetchall()
            
            conn.close()
            
            results = []
            for row in rows:
                bookmark = Bookmark(
                    id=row[0],
                    book_id=row[1],
                    page_number=row[2],
                    timestamp=row[3]
                )
                book = Book(
                    id=row[4],
                    title=row[5],
                    author=row[6],
                    category=row[7],
                    year=row[8],
                    description=row[9],
                    cover=row[10],
                    pdf=row[11],
                    file_size=row[12],
                    pages=row[13],
                    copyright_protected=bool(row[14]) if len(row) > 14 else False,
                    view_count=int(row[15]) if len(row) > 15 else 0,
                    download_count=int(row[16]) if len(row) > 16 else 0
                )
                results.append((bookmark, book))
            return results
        except Exception as e:
            logger.error(f"Ошибка получения закладок с книгами: {e}", exc_info=True)
            conn.close()
            return []

    def get_all_books(self) -> List[Book]:
        """Получает все книги из базы данных"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM books ORDER BY id")
            rows = cursor.fetchall()

            books = []
            for row in rows:
                book = Book(
                    id=row[0], title=row[1], author=row[2], category=row[3], year=row[4],
                    description=row[5], cover=row[6], pdf=row[7], file_size=row[8], pages=row[9],
                    copyright_protected=bool(row[10]) if len(row) > 10 else False,
                    view_count=int(row[11]) if len(row) > 11 else 0,
                    download_count=int(row[12]) if len(row) > 12 else 0
                )
                books.append(book)

            conn.close()
            return books
        except Exception as e:
            logger.error(f"Ошибка получения книг из базы данных: {e}", exc_info=True)
            conn.close()
            return []

    def get_book_by_pdf(self, pdf_path: str) -> Optional[Book]:
        """Получает книгу по пути к PDF-файлу"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM books WHERE pdf=?", (pdf_path,))
            row = cursor.fetchone()
            
            if row:
                book = Book(
                    id=row[0], title=row[1], author=row[2], category=row[3], year=row[4],
                    description=row[5], cover=row[6], pdf=row[7], file_size=row[8], pages=row[9],
                    copyright_protected=bool(row[10]) if len(row) > 10 else False,
                    view_count=int(row[11]) if len(row) > 11 else 0,
                    download_count=int(row[12]) if len(row) > 12 else 0
                )
                conn.close()
                return book
            else:
                conn.close()
                return None
        except Exception as e:
            logger.error(f"Ошибка получения книги из базы данных: {e}", exc_info=True)
            conn.close()
            return None

    def search_books(self, query: str) -> List[Book]:
        """Поиск книг по названию или автору"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM books
                WHERE title LIKE ? OR author LIKE ?
                ORDER BY id
            """, (f"%{query}%", f"%{query}%"))
            
            rows = cursor.fetchall()
            
            books = []
            for row in rows:
                book = Book(
                    id=row[0], title=row[1], author=row[2], category=row[3], year=row[4],
                    description=row[5], cover=row[6], pdf=row[7], file_size=row[8], pages=row[9],
                    copyright_protected=bool(row[10]) if len(row) > 10 else False,
                    view_count=int(row[11]) if len(row) > 11 else 0,
                    download_count=int(row[12]) if len(row) > 12 else 0
                )
                books.append(book)
            
            conn.close()
            return books
        except Exception as e:
            logger.error(f"Ошибка поиска книг в базе данных: {e}", exc_info=True)
            conn.close()
            return []

    def clear_books(self):
        """Очищает таблицу с книгами"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Перед очисткой, логируем информацию об удаляемых книгах для аналитики
            cursor.execute("SELECT * FROM books")
            all_books_rows = cursor.fetchall()
            books_to_delete = []
            for row in all_books_rows:
                book = Book(
                    id=row[0], title=row[1], author=row[2], category=row[3], year=row[4],
                    description=row[5], cover=row[6], pdf=row[7], file_size=row[8], pages=row[9],
                    copyright_protected=bool(row[10]) if len(row) > 10 else False,
                    view_count=int(row[11]) if len(row) > 11 else 0,
                    download_count=int(row[12]) if len(row) > 12 else 0
                )
                books_to_delete.append(book)

            cursor.execute("DELETE FROM books")
            
            conn.commit()
            conn.close()

            # Отслеживаем удаление каждой книги
            for book in books_to_delete:
                self.analytics.track_book_deleted(book)
        except Exception as e:
            logger.error(f"Ошибка очистки таблицы книг: {e}", exc_info=True)
            conn.close()

