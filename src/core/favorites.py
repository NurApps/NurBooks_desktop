"""
Менеджер избранного с синхронизацией по пользователю.

- Онлайн: источник истины — Firestore (через API-сервер, скоуп по userId).
- Офлайн: локальный кэш data/favorite_books.json.
"""
from src.core.synced_list import SyncedListManager


class FavoritesManager(SyncedListManager):
    def __init__(self):
        super().__init__(
            collection_name="favorites",
            file_name="favorite_books.json",
            log_label="избранное",
            server_get="get_favorites",
            server_add="add_favorite",
            server_remove="remove_favorite",
            display_name="Избранное",
            check_method_name="is_favorite",
            get_method_name="get_favorites",
        )


favorites = FavoritesManager()
