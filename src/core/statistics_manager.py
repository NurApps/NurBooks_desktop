import threading

from src.core.database import Database
from src.core.logger import get_logger

logger = get_logger(__name__)


class StatisticsManager:
    """
    Централизованный менеджер статистики.
    Вся статистика идёт в Firestore.
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
        self._use_firebase = self._check_firebase_available()
        self._initialized = True
        logger.info(f"StatisticsManager: Firebase={self._use_firebase}")

    def _check_firebase_available(self) -> bool:
        try:
            from src.core.firebase_client import firebase_client
            return firebase_client.is_initialized()
        except Exception:
            return False

    def increment_view_count(self, book_id: int) -> bool:
        try:
            if self._use_firebase:
                from src.core.firebase_client import firebase_client
                result = firebase_client.increment_view_count(book_id)
                firebase_client.log_analytics_event('view', book_id)
                return result
            else:
                return self.database.increment_book_view_count(book_id)
        except Exception as e:
            logger.error(f"Ошибка при увеличении просмотров: {e}", exc_info=True)
            self._use_firebase = False
            try:
                return self.database.increment_book_view_count(book_id)
            except Exception:
                return False

    def increment_download_count(self, book_id: int) -> bool:
        try:
            if self._use_firebase:
                from src.core.firebase_client import firebase_client
                result = firebase_client.increment_download_count(book_id)
                firebase_client.log_analytics_event('download', book_id)
                return result
            else:
                return self.database.increment_book_download_count(book_id)
        except Exception as e:
            logger.error(f"Ошибка при увеличении скачиваний: {e}", exc_info=True)
            self._use_firebase = False
            try:
                return self.database.increment_book_download_count(book_id)
            except Exception:
                return False

    def get_statistics(self, book_id: int) -> dict:
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


# Алиас для удобства
stats = StatisticsManager()
