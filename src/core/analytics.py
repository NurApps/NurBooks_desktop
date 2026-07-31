from typing import Any


class Analytics:
    """No-op — вся аналитика идёт через Firebase"""

    def __init__(self):
        pass

    def init_db(self):
        pass

    def log_view(self, book_id: int, user_id: str | None = None,
                 ip_address: str | None = None) -> bool:
        return True

    def log_download(self, book_id: int, file_size: str | None = None,
                     user_id: str | None = None, ip_address: str | None = None) -> bool:
        return True

    def get_views_count(self, book_id: int) -> int:
        return 0

    def get_downloads_count(self, book_id: int) -> int:
        return 0

    def get_book_statistics(self, book_id: int) -> dict[str, Any]:
        return {'book_id': book_id, 'views': 0, 'downloads': 0, 'view_to_download_ratio': 0}

    def track_book_added(self, book) -> None:
        pass

    def track_book_updated(self, book) -> None:
        pass

    def track_book_deleted(self, book) -> None:
        pass

    def track_bookmark_added(self, bookmark) -> None:
        pass

    def track_bookmark_deleted(self, bookmark) -> None:
        pass
