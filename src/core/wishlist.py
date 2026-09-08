"""
Менеджер «Хочу прочитать» (вишлист) с синхронизацией по пользователю.

- Онлайн: источник истины — Firestore (через API-сервер, скоуп по userId).
- Офлайн: локальный кэш data/wishlist.json.
"""
from src.core.synced_list import SyncedListManager


class WishlistManager(SyncedListManager):
    def __init__(self):
        super().__init__(
            collection_name="wishlist",
            file_name="wishlist.json",
            log_label="вишлист",
            server_get="get_wishlist",
            server_add="add_wishlist",
            server_remove="remove_wishlist",
            display_name="Хочу прочитать",
            check_method_name="is_in_wishlist",
            get_method_name="get_wishlist",
        )


wishlist = WishlistManager()
