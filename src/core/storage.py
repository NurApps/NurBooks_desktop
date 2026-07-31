import json
import os
import threading
import time
import urllib.request

from src.config import DEFAULT_DATA_PATH, DEFAULT_PDFS_PATH, NURBOOKS_DOWNLOADS_PATH
from src.core.author_manager import AuthorManager
from src.core.database import Database
from src.core.models import Author, Book, UserSettings


class Storage:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, github_base_url: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, github_base_url: str = None):
        if self._initialized:
            return
        self.data_path = DEFAULT_DATA_PATH
        self.pdfs_path = DEFAULT_PDFS_PATH
        self.downloads_path = NURBOOKS_DOWNLOADS_PATH
        self.github_base_url = github_base_url
        self._extract_initial_data()
        self.ensure_directories()
        self.database = Database()
        self.author_manager = AuthorManager()

        # Кэш в памяти
        self._books_cache = None
        self._authors_cache = None
        self._thumbnail_cache = {}
        self._last_load_time = 0
        self._cache_ttl = 30  # секунд — принудительно обновляем раз в 30 сек
        self._initialized = True

    def _convert_to_raw_url(self, url: str) -> str:
        """Конвертирует GitHub blob URL в raw URL для прямого доступа к файлу"""
        if not url:
            return url

        if "github.com" in url and "/blob/" in url:
            return url.replace("/blob/", "/raw/")
        return url

    def download_from_github(self, github_url: str, filename: str = None) -> str | None:
        """
        Скачивает файл из GitHub в системную папку загрузок.
        Возвращает путь к скачанному файлу или None при ошибке.
        """
        try:
            # Конвертируем URL в raw формат
            raw_url = self._convert_to_raw_url(github_url)

            # Если это не URL, возвращаем None
            if not raw_url.startswith(('http://', 'https://')):
                return None

            # Определяем имя файла
            if not filename:
                filename = os.path.basename(raw_url.split('?')[0])

            # Создаем папку загрузок, если не существует
            os.makedirs(self.downloads_path, exist_ok=True)

            # Полный путь для сохранения
            save_path = os.path.join(self.downloads_path, filename)

            # Скачиваем файл
            urllib.request.urlretrieve(raw_url, save_path)

            return save_path
        except Exception as e:
            print(f"Ошибка скачивания из GitHub: {e}")
            return None

    def download_book_pdf(self, book: Book) -> str | None:
        """
        Скачивает PDF книги из GitHub в папку загрузок.
        Возвращает путь к скачанному файлу или None при ошибке.
        """
        if not book.pdf:
            return None

        # Если это уже локальный путь и файл существует, возвращаем его
        if os.path.exists(book.pdf):
            return book.pdf

        # Скачиваем из GitHub
        filename = f"{book.title}.pdf" if book.title else os.path.basename(book.pdf)
        return self.download_from_github(book.pdf, filename)

    def _extract_initial_data(self):
        """Нет начальных данных — всё через Firebase и GitHub"""

    def ensure_directories(self):
        """Создает необходимые директории"""
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(self.pdfs_path, exist_ok=True)
        os.makedirs("saved_books", exist_ok=True)
        os.makedirs("assets/icons", exist_ok=True)
        os.makedirs("data/thumbnails", exist_ok=True)

    def load_books(self, force: bool = False) -> list[Book]:
        """Загружает книги с кэшированием (TTL 30 сек при активном Firebase).

        Источник: Firestore через API-сервер, при недоступности — локальный SQLite-кэш.
        """
        now = time.time()
        ttl_expired = (now - self._last_load_time) > self._cache_ttl

        if self._books_cache is not None and not force and not ttl_expired:
            return self._books_cache

        self._last_load_time = now

        books = self.database.get_all_books()
        for book in books:
            book.cover = self.find_thumbnail_for_book(book)
        self._books_cache = books
        return books

    def invalidate_books_cache(self):
        """Сбрасывает кэш книг"""
        self._books_cache = None

    def find_thumbnail_for_book(self, book: Book) -> str | None:
        """Находит/скачивает обложку для книги (с кэшированием)"""
        cache_key = id(book)
        if cache_key in self._thumbnail_cache:
            return self._thumbnail_cache[cache_key]

        if not book.cover:
            self._thumbnail_cache[cache_key] = None
            return None

        # 1. Локальный файл — существует
        if os.path.exists(book.cover):
            self._thumbnail_cache[cache_key] = book.cover
            return book.cover

        # 2. Локальный файл в data/thumbnails/
        filename = os.path.basename(book.cover)
        thumbs_path = os.path.join(self.data_path, "thumbnails", filename)

        # 3. URL — скачиваем и сохраняем локально
        if book.cover.startswith(('http://', 'https://')):
            raw_url = book.cover.replace("/blob/", "/raw/") if "github.com" in book.cover else book.cover

            # Если уже скачан — используем локальную копию
            if os.path.exists(thumbs_path):
                self._thumbnail_cache[cache_key] = thumbs_path
                return thumbs_path

            # Скачиваем в фоне
            try:
                os.makedirs(os.path.dirname(thumbs_path), exist_ok=True)
                urllib.request.urlretrieve(raw_url, thumbs_path)
                self._thumbnail_cache[cache_key] = thumbs_path
                return thumbs_path
            except Exception as e:
                print(f"Ошибка скачивания обложки: {e}")
                # fallback — возвращаем raw URL, Flet скачает сам
                self._thumbnail_cache[cache_key] = raw_url
                return raw_url

        # 4. Существующий путь в data/thumbnails/ (если не URL)
        if os.path.exists(thumbs_path):
            self._thumbnail_cache[cache_key] = thumbs_path
            return thumbs_path

        self._thumbnail_cache[cache_key] = None
        return None

    def load_authors(self, force: bool = False) -> list[Author]:
        """Загружает авторов с кэшированием."""
        if self._authors_cache is not None and not force:
            return self._authors_cache
        self._authors_cache = self.author_manager.load_authors()
        return self._authors_cache

    def invalidate_authors_cache(self):
        """Сбрасывает кэш авторов"""
        self._authors_cache = None

    def save_books(self, books: list[Book]):
        """Сохраняет книги в базу данных SQLite"""
        # Очищаем таблицу и добавляем все книги заново
        self.database.clear_books()
        for book in books:
            # Нормализуем URL перед сохранением (конвертируем blob в raw)
            if book.cover and book.cover.startswith(('http://', 'https://')):
                book.cover = self._convert_to_raw_url(book.cover)
            if book.pdf and book.pdf.startswith(('http://', 'https://')):
                book.pdf = self._convert_to_raw_url(book.pdf)
            self.database.add_book(book)

    def save_authors(self, authors: list[Author]):
        """Сохраняет авторов через AuthorManager"""
        self.author_manager.save_authors(authors)

    def _resolve_download_path(self, path: str) -> str:
        """Разрешает путь загрузки: 'downloads' -> реальный путь в ~/Downloads/downloads-nurbooks"""
        if path == "downloads":
            return NURBOOKS_DOWNLOADS_PATH
        return path

    def load_settings(self) -> UserSettings:
        """Загружает настройки пользователя"""
        try:
            with open(f"{self.data_path}/settings.json", encoding="utf-8") as f:
                data = json.load(f)
            # Обратная совместимость: старый ключ enable云flare_storage → enable_cloudflare_storage
            if "enable云flare_storage" in data:
                data["enable_cloudflare_storage"] = data.pop("enable云flare_storage")
            # Отбрасываем неизвестные ключи (битые/устаревшие настройки не должны ронять загрузку)
            known_fields = UserSettings.__dataclass_fields__.keys()
            data = {k: v for k, v in data.items() if k in known_fields}
            settings = UserSettings(**data)
            settings.default_path = self._resolve_download_path(settings.default_path)
            return settings
        except FileNotFoundError:
            return UserSettings(default_path=NURBOOKS_DOWNLOADS_PATH)
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            return UserSettings(default_path=NURBOOKS_DOWNLOADS_PATH)

    def save_settings(self, settings: UserSettings):
        """Сохраняет настройки пользователя"""
        try:
            with open(f"{self.data_path}/settings.json", "w", encoding="utf-8") as f:
                json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")


