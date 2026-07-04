from typing import List, Optional
from src.core.models import Book, Bookmark
from src.core.logger import get_logger

logger = get_logger(__name__)


class Database:
    def __init__(self, data_path=None):
        self._firebase = None
        try:
            from src.core.firebase_client import firebase_client
            self._firebase = firebase_client
        except Exception as e:
            logger.warning(f"Не удалось загрузить FirebaseClient: {e}")

    def _fb(self):
        if self._firebase and self._firebase.is_initialized():
            return self._firebase
        return None

    def init_db(self):
        pass

    def get_connection(self):
        return None

    def _normalize_path(self, path: str) -> Optional[str]:
        return path

    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        fb = self._fb()
        if fb:
            return fb.get_book_by_id(book_id)
        return None

    def add_book(self, book: Book) -> str:
        fb = self._fb()
        if fb:
            return fb.add_book(book)
        return "error"

    def update_book(self, book: Book) -> bool:
        fb = self._fb()
        if fb:
            return fb.update_book(book)
        return False

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
        fb = self._fb()
        if fb:
            return fb.delete_book(book_id)
        return False

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

    def get_bookmarks_by_book(self, book_id: int) -> List[Bookmark]:
        fb = self._fb()
        if fb:
            return fb.get_bookmarks_by_book(book_id)
        return []

    def get_all_bookmarks_with_books(self) -> List:
        fb = self._fb()
        if fb:
            return fb.get_all_bookmarks_with_books()
        return []

    def save_reading_progress(self, book_id: int, page_number: int) -> bool:
        fb = self._fb()
        if fb:
            return fb.save_reading_progress(book_id, page_number)
        return False

    def get_reading_progress(self, book_id: int) -> Optional[int]:
        fb = self._fb()
        if fb:
            result = fb.get_reading_progress(book_id)
            return result if result else None
        return None

    def get_all_reading_progress(self) -> dict:
        fb = self._fb()
        if fb:
            return fb.get_all_reading_progress()
        return {}

    def get_all_books(self) -> List[Book]:
        fb = self._fb()
        if fb:
            return fb.get_all_books()
        return []

    def get_book_by_pdf(self, pdf_path: str) -> Optional[Book]:
        fb = self._fb()
        if fb:
            return fb.get_book_by_pdf(pdf_path)
        return None

    def search_books(self, query: str) -> List[Book]:
        fb = self._fb()
        if fb:
            return fb.search_books(query)
        return []

    def clear_books(self):
        fb = self._fb()
        if fb:
            fb.clear_books()
