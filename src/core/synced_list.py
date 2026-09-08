"""
Базовый менеджер синхронизируемого списка с локальным кэшем.

- Онлайн: источник истины — Firestore (через API-сервер, скоуп по userId).
- Офлайн: локальный JSON-кэш.
"""
import json
import os
import threading

from src.core.logger import get_logger

logger = get_logger(__name__)


class SyncedListManager:
    """Параметризуемый менеджер списка с серверной синхронизацией."""

    _instances: dict[str, "SyncedListManager"] = {}
    _class_lock = threading.Lock()

    def __new__(cls, **kwargs):
        key = kwargs.get("collection_name", cls.__name__)
        if key not in cls._instances:
            with cls._class_lock:
                if key not in cls._instances:
                    inst = super().__new__(cls)
                    inst._initialized_flag = False
                    cls._instances[key] = inst
        return cls._instances[key]

    def __init__(self, *, collection_name: str, file_name: str, log_label: str,
                 server_get: str, server_add: str, server_remove: str,
                 display_name: str, check_method_name: str, get_method_name: str):
        if self._initialized_flag:
            return
        from src.config import DEFAULT_DATA_PATH
        self._collection_name = collection_name
        self._file_path = os.path.join(DEFAULT_DATA_PATH, file_name)
        self._items: list[str] = []
        self._loaded = False
        self._log_label = log_label
        self._server_get = server_get
        self._server_add = server_add
        self._server_remove = server_remove
        self._display_name = display_name
        self._check_method_name = check_method_name
        self._get_method_name = get_method_name
        self._initialized_flag = True
        self._load_local()

    # -- Backward-compatible property aliases for tests --

    @property
    def _favorites(self) -> list[str]:
        return self._items

    @_favorites.setter
    def _favorites(self, value: list[str]):
        self._items = value

    @property
    def _wishlist(self) -> list[str]:
        return self._items

    @_wishlist.setter
    def _wishlist(self, value: list[str]):
        self._items = value

    # -- Persistence --

    def _load_local(self):
        try:
            if os.path.exists(self._file_path):
                with open(self._file_path, encoding="utf-8") as f:
                    data = json.load(f)
                self._items = [str(x) for x in data] if isinstance(data, list) else []
            self._loaded = True
        except Exception as e:
            logger.warning(f"Не удалось загрузить {self._log_label}: {e}")
            self._items = []
            self._loaded = True

    def _save_local(self):
        try:
            os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump(self._items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Не удалось сохранить {self._log_label}: {e}")

    def _sync_from_server(self) -> bool:
        try:
            from src.core.firebase_client import firebase_client
            if not firebase_client.is_initialized():
                return False
            server = getattr(firebase_client, self._server_get)()
            if server is None:
                return False
            self._items = list(server)
            self._loaded = True
            self._save_local()
            return True
        except Exception as e:
            logger.warning(f"Не удалось синхронизировать {self._log_label}: {e}")
            return False

    def load(self):
        """Загружает список: сначала сервер, при недоступности — локальный кэш."""
        if not self._sync_from_server():
            self._load_local()

    def get_items(self) -> list[str]:
        if not self._loaded:
            self.load()
        return list(self._items)

    # -- Backward-compatible getter aliases --

    def get_favorites(self) -> list[str]:
        return self.get_items()

    def get_wishlist(self) -> list[str]:
        return self.get_items()

    def is_favorite(self, book_id) -> bool:
        return str(book_id) in self.get_items()

    def is_in_wishlist(self, book_id) -> bool:
        return str(book_id) in self.get_items()

    def contains(self, book_id) -> bool:
        return str(book_id) in self.get_items()

    def add(self, book_id) -> bool:
        bid = str(book_id)
        self.get_items()
        if bid not in self._items:
            self._items.append(bid)
            self._save_local()
            try:
                from src.core.firebase_client import firebase_client
                if firebase_client.is_initialized():
                    return getattr(firebase_client, self._server_add)(int(bid))
            except Exception as e:
                logger.warning(f"Не удалось отправить в {self._log_label}: {e}")
        return True

    def remove(self, book_id) -> bool:
        bid = str(book_id)
        self.get_items()
        if bid in self._items:
            self._items.remove(bid)
            self._save_local()
            try:
                from src.core.firebase_client import firebase_client
                if firebase_client.is_initialized():
                    return getattr(firebase_client, self._server_remove)(int(bid))
            except Exception as e:
                logger.warning(f"Не удалось удалить из {self._log_label}: {e}")
        return True
