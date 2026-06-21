"""
Прокси-менеджер баз данных для NurBooks GUI

Позволяет переключаться между SQLite и Firestore БД.
Используется в add_book_gui.py для единого интерфейса работы с БД.
"""

from typing import Optional, List
from src.core.models import Book, Bookmark
from src.core.database import Database as SQLiteDatabase
from scripts.firestore_db_manager import FirestoreBookManager as FirestoreDatabase

class DatabaseProxy:
    """
    Прокси-класс для управления SQLite и Firestore.
    
    Позволяет:
    - Переключаться между SQLite и Firestore
    - Использовать один общий интерфейс
    - Сохранять текущий тип БД
    """
    
    def __init__(self, db_type: str = "sqlite"):
        """
        Инициализирует прокси.
        
        Args:
            db_type: Тип БД - "sqlite" или "firestore"
        """
        self.db_type = db_type
        self._sqlite_db = None
        self._firestore_db = None
        
        self._initialize_dbs()
    
    def _initialize_dbs(self):
        """Инициализирует обе базы данных."""
        self._sqlite_db = SQLiteDatabase()
        self._firestore_db = FirestoreDatabase()
    
    def set_db_type(self, db_type: str):
        """
        Устанавливает текущую БД.
        
        Args:
            db_type: Тип БД - "sqlite" или "firestore"
        """
        if db_type not in ["sqlite", "firestore"]:
            raise ValueError(f"Недопустимый тип БД: {db_type}")
        
        self.db_type = db_type
        
        if db_type == "firestore":
            if not self._firestore_db.is_initialized():
                raise RuntimeError("Firestore не инициализирован. Проверьте serviceAccountKey.json")
    
    def get_current_db(self):
        """
        Возвращает текущую активную БД.
        
        Returns:
            SQLiteDatabase или FirestoreDatabase
        """
        if self.db_type == "firestore":
            return self._firestore_db
        else:
            return self._sqlite_db
    
    # ========== Books ==========
    
    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        """Получает книгу по ID"""
        return self.get_current_db().get_book_by_id(book_id)
    
    def get_all_books(self) -> List[Book]:
        """Получает все книги"""
        return self.get_current_db().get_all_books()
    
    def search_books(self, query: str) -> List[Book]:
        """Поиск книг"""
        return self.get_current_db().search_books(query)
    
    def add_book(self, book: Book) -> str:
        """Добавляет книгу"""
        return self.get_current_db().add_book(book)
    
    def update_book(self, book: Book) -> bool:
        """Обновляет книгу"""
        return self.get_current_db().update_book(book)
    
    def delete_book(self, book_id: int) -> bool:
        """Удаляет книгу по ID"""
        return self.get_current_db().delete_book(book_id)
    
    def get_book_by_pdf(self, pdf_path: str) -> Optional[Book]:
        """Получает книгу по PDF"""
        return self.get_current_db().get_book_by_pdf(pdf_path)
    
    def clear_books(self):
        """Очищает таблицу книг"""
        if self.db_type == "sqlite":
            self._sqlite_db.clear_books()
        else:
            # Для Firestore нет метода clear_books, поэтому удаляем все BOOKS
            books = self._firestore_db.get_all_books()
            for book in books:
                self._firestore_db.delete_book(book.id)
    
    # ========== Analytics ==========
    
    def increment_book_view_count(self, book_id: int) -> bool:
        """Увеличивает счётчик просмотров"""
        if self.db_type == "sqlite":
            return self._sqlite_db.increment_book_view_count(book_id)
        else:
            return self._firestore_db.increment_view_count(book_id)
    
    def increment_book_download_count(self, book_id: int) -> bool:
        """Увеличивает счётчик скачиваний"""
        if self.db_type == "sqlite":
            return self._sqlite_db.increment_book_download_count(book_id)
        else:
            return self._firestore_db.increment_download_count(book_id)
    
    # ========== Bookmarks ==========
    
    def add_bookmark(self, bookmark: Bookmark) -> bool:
        """Добавляет закладку"""
        return self.get_current_db().add_bookmark(bookmark)
    
    def get_bookmarks_by_book(self, book_id: int) -> List[Bookmark]:
        """Получает закладки для книги"""
        return self.get_current_db().get_bookmarks_by_book(book_id)
    
    def get_all_bookmarks_with_books(self) -> List:
        """Получает все закладки с информацией о книгах"""
        return self.get_current_db().get_all_bookmarks_with_books()
    
    def delete_bookmark(self, bookmark_id: int) -> bool:
        """Удаляет закладку"""
        return self.get_current_db().delete_bookmark(bookmark_id)
    
    # ========== Utility ==========
    
    def is_firestore_initialized(self) -> bool:
        """Проверяет, инициализирован ли Firestore"""
        return self._firestore_db.is_initialized()
    
    def get_db_type(self) -> str:
        """Возвращает текущий тип БД"""
        return self.db_type


# Singleton instance
db_proxy = DatabaseProxy()
