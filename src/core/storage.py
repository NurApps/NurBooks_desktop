import json
import os
import sys
import shutil
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.core.models import Book, Author, UserSettings, Notification
from src.config import DEFAULT_DATA_PATH, DEFAULT_PDFS_PATH, NURBOOKS_DOWNLOADS_PATH
from src.core.database import Database
from src.core.firebase_client import firebase_client
from src.core.author_manager import AuthorManager

class Storage:
    def __init__(self, github_base_url: str = None):
        self.data_path = DEFAULT_DATA_PATH
        self.pdfs_path = DEFAULT_PDFS_PATH
        self.downloads_path = NURBOOKS_DOWNLOADS_PATH  # Папка downloads-nurbooks в Загрузках
        self.github_base_url = github_base_url  # Базовый URL GitHub репозитория
        self._extract_initial_data()  # Распаковываем данные перед использованием
        self.ensure_directories()
        self.database = Database()
        self.author_manager = AuthorManager()
        self.db_path = os.path.join(self.data_path, "books.db")

    def _convert_to_raw_url(self, url: str) -> str:
        """Конвертирует GitHub blob URL в raw URL для прямого доступа к файлу"""
        if not url:
            return url
        
        if "github.com" in url and "/blob/" in url:
            return url.replace("/blob/", "/raw/")
        return url

    def download_from_github(self, github_url: str, filename: str = None) -> Optional[str]:
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

    def download_book_pdf(self, book: Book) -> Optional[str]:
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
        """Распаковывает начальные данные из EXE, если они отсутствуют"""
        # Работаем только если запущены как EXE
        if not getattr(sys, 'frozen', False):
            return

        # Путь к ресурсам внутри EXE (_MEIPASS)
        # В Python 3.12+ нужно использовать getattr для доступа к _MEIPASS
        base_internal_path = getattr(sys, '_MEIPASS', None)
        if base_internal_path is None:
            return  # Если _MEIPASS недоступен, выходим
        
        # 1. Распаковка папки data (база данных, авторы, обложки)
        internal_data = os.path.join(base_internal_path, "data")
        
        # Убрали условие "and not books.db", чтобы проверять содержимое внутри (например, картинки)
        if os.path.exists(internal_data):
            try:
                if not os.path.exists(self.data_path):
                    shutil.copytree(internal_data, self.data_path)
                else:
                    # Если папка data есть, аккуратно дописываем недостающее
                    
                    # 1.1 Обложки (thumbnails) - копируем отсутствующие
                    internal_thumbs = os.path.join(internal_data, "thumbnails")
                    target_thumbs = os.path.join(self.data_path, "thumbnails")
                    if os.path.exists(internal_thumbs):
                        os.makedirs(target_thumbs, exist_ok=True)
                        for item in os.listdir(internal_thumbs):
                            s = os.path.join(internal_thumbs, item)
                            d = os.path.join(target_thumbs, item)
                            if not os.path.exists(d):
                                shutil.copy2(s, d)

                    # 1.2 База данных и авторы (копируем ТОЛЬКО если их нет)
                    for filename in ["books.db", "authors.json"]:
                        s = os.path.join(internal_data, filename)
                        d = os.path.join(self.data_path, filename)
                        if os.path.exists(s) and not os.path.exists(d):
                            shutil.copy2(s, d)
            except Exception as e:
                print(f"Ошибка распаковки data: {e}")

        # 2. Распаковка папки pdfs
        internal_pdfs = os.path.join(base_internal_path, "pdfs")
        if os.path.exists(internal_pdfs) and not os.path.exists(self.pdfs_path):
            try:
                shutil.copytree(internal_pdfs, self.pdfs_path)
            except Exception as e:
                print(f"Ошибка распаковки pdfs: {e}")

    def ensure_directories(self):
        """Создает необходимые директории"""
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(self.pdfs_path, exist_ok=True)
        os.makedirs("saved_books", exist_ok=True)
        os.makedirs("assets/icons", exist_ok=True)
        os.makedirs("data/thumbnails", exist_ok=True)

    def load_books(self) -> List[Book]:
        """
        Загружает книги. Сначала пробует Firebase, если он инициализирован.
        Если нет — использует локальную БД SQLite.
        """
        if firebase_client.is_initialized():
            books = firebase_client.get_all_books()
            if books:
                # Опционально: можно синхронизировать локальную БД здесь
                return books
        
        # Fallback на локальную БД
        books = self.database.get_all_books()
        
        # Обновляем пути к обложкам для каждой книги
        for book in books:
            # Проверяем валидность пути или URL. Если не найдено - будет None.
            book.cover = self.find_thumbnail_for_book(book)
        return books

    def find_thumbnail_for_book(self, book: Book) -> Optional[str]:
        """Находит путь к обложке для книги"""
        
        if not book.cover:
            return None

        # 1. Если это URL
        if book.cover.startswith(('http://', 'https://')):
            # Автоматически исправляем ссылки GitHub blob на raw для корректного отображения
            if "github.com" in book.cover and "/blob/" in book.cover:
                return book.cover.replace("/blob/", "/raw/")
            return book.cover
            
        # 2. Проверяем локальный путь (абсолютный или относительный)
        if os.path.exists(book.cover):
            return book.cover
            
        # 3. Проверяем в папке thumbnails по имени файла
        filename = os.path.basename(book.cover)
        thumbs_path = os.path.join(self.data_path, "thumbnails", filename)
        if os.path.exists(thumbs_path):
            return thumbs_path
            
        return None

    def load_authors(self) -> List[Author]:
        """Загружает авторов через AuthorManager"""
        return self.author_manager.load_authors()

    def save_books(self, books: List[Book]):
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

    def save_authors(self, authors: List[Author]):
        """Сохраняет авторов через AuthorManager"""
        self.author_manager.save_authors(authors)

    def load_settings(self) -> UserSettings:
        """Загружает настройки пользователя"""
        try:
            with open(f"{self.data_path}/settings.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return UserSettings(**data)
        except FileNotFoundError:
            return UserSettings(default_path="downloads")
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            return UserSettings(default_path="downloads")

    def save_settings(self, settings: UserSettings):
        """Сохраняет настройки пользователя"""
        try:
            with open(f"{self.data_path}/settings.json", "w", encoding="utf-8") as f:
                json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    
