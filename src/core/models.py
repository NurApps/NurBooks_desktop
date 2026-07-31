from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class Book:
    id: int
    title: str
    author: str
    category: str
    year: int
    description: str
    cover: str
    pdf: str
    file_size: str | None = None
    pages: int | None = None
    copyright_protected: bool = False
    view_count: int = 0
    download_count: int = 0

    def to_dict(self):
        return asdict(self)

@dataclass
class Author:
    id: int
    name: str
    bio: str
    books: list[int]

    def to_dict(self):
        return asdict(self)

@dataclass
class UserSettings:
    default_path: str
    theme: str = "light"
    language: str = "ru"
    pdf_reader: str = "ask"  # "ask" - спрашивать, "builtin" - встроенная, "system" - системная
    download_notifications: bool = True
    sound_notifications: bool = True
    update_notifications: bool = True
    background_notifications: bool = True
    # Cloudflare и API
    cloudflare_api_token: str = ""
    cloudflare_account_id: str = ""
    cloudflare_bucket_name: str = ""
    enable_cloudflare_storage: bool = False

    # Обновления
    auto_update: bool = False
    beta_updates: bool = False

    # Аутентификация и приватность
    require_auth: bool = False
    jwt_secret_key: str = ""

    def to_dict(self):
        return asdict(self)

@dataclass
class Notification:
    id: int
    title: str
    message: str
    type: str  # success, error, warning, info
    timestamp: datetime

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.type,
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class Bookmark:
    """Закладка для отмеченного места в книге"""
    id: int
    book_id: int
    page_number: int
    timestamp: str  # ISO формат даты и времени

    def to_dict(self):
        return asdict(self)

