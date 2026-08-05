"""
Менеджер «Хочу прочитать» (вишлист) с синхронизацией по пользователю.

- Онлайн: источник истины — Firestore (через API-сервер, скоуп по userId).
- Офлайн: локальный кэш data/wishlist.json.
"""
import json
import os
import threading

from src.core.logger import get_logger

logger = get_logger(__name__)


class WishlistManager:
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
        from src.config import DEFAULT_DATA_PATH
        self._file_path = os.path.join(DEFAULT_DATA_PATH, "wishlist.json")
        self._wishlist: list[str] = []
        self._loaded = False
        self._initialized = True
        self._load_local()

    def _load_local(self):
        try:
            if os.path.exists(self._file_path):
                with open(self._file_path, encoding="utf-8") as f:
                    data = json.load(f)
                self._wishlist = [str(w) for w in data] if isinstance(data, list) else []
            self._loaded = True
        except Exception as e:
            logger.warning(f"Не удалось загрузить вишлист: {e}")
            self._wishlist = []
            self._loaded = True

    def _save_local(self):
        try:
            os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump(self._wishlist, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Не удалось сохранить вишлист: {e}")

    def _sync_from_server(self) -> bool:
        try:
            from src.core.firebase_client import firebase_client
            if not firebase_client.is_initialized():
                return False
            server = firebase_client.get_wishlist()
            if server is None:
                return False
            self._wishlist = list(server)
            self._loaded = True
            self._save_local()
            return True
        except Exception as e:
            logger.warning(f"Не удалось синхронизировать вишлист: {e}")
            return False

    def load(self):
        """Загружает вишлист: сначала сервер, при недоступности — локальный кэш."""
        if not self._sync_from_server():
            self._load_local()

    def get_wishlist(self) -> list[str]:
        if not self._loaded:
            self.load()
        return list(self._wishlist)

    def is_in_wishlist(self, book_id) -> bool:
        return str(book_id) in self.get_wishlist()

    def add(self, book_id) -> bool:
        bid = str(book_id)
        self.get_wishlist()
        if bid not in self._wishlist:
            self._wishlist.append(bid)
            self._save_local()
            try:
                from src.core.firebase_client import firebase_client
                if firebase_client.is_initialized():
                    return firebase_client.add_wishlist(int(bid))
            except Exception as e:
                logger.warning(f"Не удалось отправить в вишлист: {e}")
        return True

    def remove(self, book_id) -> bool:
        bid = str(book_id)
        self.get_wishlist()
        if bid in self._wishlist:
            self._wishlist.remove(bid)
            self._save_local()
            try:
                from src.core.firebase_client import firebase_client
                if firebase_client.is_initialized():
                    return firebase_client.remove_wishlist(int(bid))
            except Exception as e:
                logger.warning(f"Не удалось удалить из вишлиста: {e}")
        return True


wishlist = WishlistManager()
