"""
Модуль для централизованного управления статистикой (просмотры, скачивания)
При включённом Firebase — данные идут в Firestore
При отключённом — сохраняется локально в SQLite
"""
import threading
from typing import Optional
from src.core.models import Book
from src.core.database import Database
from src.core.analytics import Analytics
from src.core.logger import get_logger

logger = get_logger(__name__)

class StatisticsManager:
    """
    Централизованный менеджер статистики для приложения.
    
    При включённом Firebase:
    - view_count / download_count → Firestore (атомарный increment)
    - Локальная база не обновляется
    
    При отключённом Firebase:
    - view_count / download_count → SQLite (fallback)
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.database = Database()
        self.analytics = Analytics()
        self._use_firebase = self._check_firebase_available()
        self._initialized = True
        logger.info(f"StatisticsManager: Firebase={self._use_firebase}")

    def _check_firebase_available(self) -> bool:
        """Проверяет, доступен ли Firebase"""
        try:
            from src.core.firebase_client import firebase_client
            return firebase_client.is_initialized()
        except Exception:
            return False

    def increment_view_count(self, book_id: int) -> bool:
        """Увеличивает счётчик просмотров книги."""
        try:
            if self._use_firebase:
                from src.core.firebase_client import firebase_client
                result = firebase_client.increment_view_count(book_id)
                firebase_client.log_analytics_event('view', book_id)
                return result
            else:
                success = self.database.increment_book_view_count(book_id)
                if success:
                    logger.debug(f"Счётчик просмотров увеличен для книги ID={book_id} (SQLite)")
                return success
        except Exception as e:
            logger.error(f"Ошибка при увеличении просмотров: {e}", exc_info=True)
            self._use_firebase = False
            try:
                return self.database.increment_book_view_count(book_id)
            except Exception:
                return False

    def increment_download_count(self, book_id: int) -> bool:
        """Увеличивает счётчик скачиваний книги."""
        try:
            if self._use_firebase:
                from src.core.firebase_client import firebase_client
                result = firebase_client.increment_download_count(book_id)
                firebase_client.log_analytics_event('download', book_id)
                return result
            else:
                success = self.database.increment_book_download_count(book_id)
                if success:
                    logger.debug(f"Счётчик скачиваний увеличен для книги ID={book_id} (SQLite)")
                return success
        except Exception as e:
            logger.error(f"Ошибка при увеличении скачиваний: {e}", exc_info=True)
            self._use_firebase = False
            try:
                return self.database.increment_book_download_count(book_id)
            except Exception:
                return False

    def get_statistics(self, book_id: int) -> dict:
        """Получает полную статистику по книге."""
        try:
            if self._use_firebase:
                from src.core.firebase_client import firebase_client
                return firebase_client.get_book_statistics(book_id)
            else:
                return self.database.get_book_statistics(book_id)
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}", exc_info=True)
            self._use_firebase = False
            try:
                return self.database.get_book_statistics(book_id)
            except Exception:
                return {'view_count': 0, 'download_count': 0, 'view_to_download_ratio': 0}

    def update_book_view_count_in_db(self, book_id: int, new_value: int) -> bool:
        """Принудительное обновление счётчика просмотров (для миграций и ручных корректировок)"""
        try:
            if self._use_firebase:
                from src.core.firebase_client import firebase_client
                doc_ref = firebase_client._db.collection('books').document(str(book_id))
                doc_ref.update({'viewCount': new_value})
                return True
            conn = self.database.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE books SET view_count = ? WHERE id = ?", (new_value, book_id))
            conn.commit()
            affected = cursor.rowcount > 0
            conn.close()
            return affected
        except Exception as e:
            logger.error(f"Ошибка при обновлении view_count: {e}", exc_info=True)
            return False

    def update_book_download_count_in_db(self, book_id: int, new_value: int) -> bool:
        """Принудительное обновление счётчика скачиваний (для миграций и ручных корректировок)"""
        try:
            if self._use_firebase:
                from src.core.firebase_client import firebase_client
                doc_ref = firebase_client._db.collection('books').document(str(book_id))
                doc_ref.update({'downloadCount': new_value})
                return True
            conn = self.database.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE books SET download_count = ? WHERE id = ?", (new_value, book_id))
            conn.commit()
            affected = cursor.rowcount > 0
            conn.close()
            return affected
        except Exception as e:
            logger.error(f"Ошибка при обновлении download_count: {e}", exc_info=True)
            return False


# Алиас для удобства
stats = StatisticsManager()