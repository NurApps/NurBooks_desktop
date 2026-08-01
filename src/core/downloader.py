import os
import shutil
import sys

import requests

from src.config import DEFAULT_DATA_PATH, NURBOOKS_DOWNLOADS_PATH
from src.core.models import Book
from src.core.utils import format_file_size


class Downloader:
    def __init__(self, download_path: str = None, database=None):
        # По умолчанию используем папку downloads-nurbooks в системной папке загрузок
        self.download_path = download_path or NURBOOKS_DOWNLOADS_PATH
        self.database = database
        # Офлайн-кэш PDF внутри данных приложения (читается без интернета)
        self.cache_path = os.path.join(DEFAULT_DATA_PATH, "pdf_cache")
        os.makedirs(self.download_path, exist_ok=True)

    def _convert_to_raw_url(self, url: str) -> str:
        """Конвертирует GitHub blob URL в raw URL для прямого доступа к файлу"""
        if not url:
            return url

        # Если уже raw ссылка
        if "raw.githubusercontent.com" in url:
            return url

        if "github.com" in url and "/blob/" in url:
            # Используем /raw/ формат - он надежнее
            return url.replace("/blob/", "/raw/")
        return url

    def _get_book_filename(self, book: Book, original_filename: str = None) -> str:
        """
        Генерирует стабильное имя файла для книги на основе ID.
        Это гарантирует, что файл останется найденным даже если название или URL изменятся.

        Args:
            book: Объект книги
            original_filename: Оригинальное имя из URL (опционально, для улучшенного имени)

        Returns:
            Имя файла в формате: id_original_name.pdf или id.pdf
        """
        # Если у нас есть оригинальное имя (извлечено из URL), используем его
        if original_filename and original_filename.endswith('.pdf'):
            # Очищаем имя файла от специальных символов
            clean_name = os.path.splitext(original_filename)[0]
            clean_name = clean_name.replace(' ', '_')[:30]  # Ограничиваем длину
            return f"{book.id}_{clean_name}.pdf"

        # Если имя файла от URL не подходит, используем название книги
        if book.title:
            clean_title = book.title.replace(' ', '_')[:30]
            return f"{book.id}_{clean_title}.pdf"

        # Резервный вариант - только ID
        return f"{book.id}.pdf"

    def download_book(self, book: Book, custom_path: str | None = None) -> str:
        """
        Скачивает книгу и возвращает путь к файлу
        """
        try:
            # Определяем путь для сохранения
            save_path = custom_path or self.download_path
            os.makedirs(save_path, exist_ok=True)

            # Конвертируем URL в raw формат (для GitHub)
            pdf_url = self._convert_to_raw_url(book.pdf)

            # Получаем исходное имя файла из URL для использования в финальном имени
            original_filename = None
            if pdf_url.startswith('http'):
                original_filename = os.path.basename(pdf_url.split('?')[0])
            else:
                original_filename = os.path.basename(pdf_url)

            # Генерируем стабильное имя файла на основе ID
            filename = self._get_book_filename(book, original_filename)

            full_path = os.path.join(save_path, filename)

            # Если книга уже скачана
            if os.path.exists(full_path):
                return full_path

            # Скачиваем книгу
            if pdf_url.startswith('http'):
                response = requests.get(pdf_url)
                response.raise_for_status()  # Проверка на ошибки HTTP
                with open(full_path, 'wb') as f:
                    f.write(response.content)
            else:
                # Если это локальный файл, копируем его
                import shutil

                source_path = pdf_url

                # Логика поиска файла, если прямой путь не работает (адаптация под устройство)
                if not os.path.exists(source_path):
                    # 1. Пробуем найти в папке pdfs относительно текущей директории
                    possible_path = os.path.join("pdfs", os.path.basename(pdf_url))
                    if os.path.exists(possible_path):
                        source_path = possible_path
                    # 2. Пробуем найти внутри ресурсов EXE (если скомпилировано)
                    # В Python 3.12+ нужно использовать getattr для доступа к _MEIPASS
                    elif getattr(sys, 'frozen', False):
                        meipass_path = getattr(sys, '_MEIPASS', None)
                        if meipass_path:
                            internal_path = os.path.join(meipass_path, "pdfs", os.path.basename(pdf_url))
                            if os.path.exists(internal_path):
                                source_path = internal_path

                if os.path.exists(source_path):
                    shutil.copy(source_path, full_path)
                else:
                    raise FileNotFoundError(f"Файл книги не найден: {pdf_url}")

            return full_path

        except Exception as e:
            raise Exception(f"Ошибка скачивания книги: {e}")

    def download_book_with_size(self, book: Book, custom_path: str | None = None) -> tuple[str, str]:
        """
        Скачивает книгу и возвращает путь к файлу и его размер в форматированном виде
        """
        try:
            # Скачиваем книгу
            file_path = self.download_book(book, custom_path)

            # Получаем размер файла
            file_size_bytes = os.path.getsize(file_path)
            formatted_size = format_file_size(file_size_bytes)

            return file_path, formatted_size

        except Exception as e:
            raise Exception(f"Ошибка скачивания книги: {e}")

    def get_downloaded_books(self) -> list[str]:
        """Получить список скачанных книг"""
        try:
            return [f for f in os.listdir(self.download_path) if f.endswith('.pdf')]
        except FileNotFoundError:
            return []

    def delete_book(self, filename: str) -> bool:
        """Удалить скачанную книгу"""
        try:
            file_path = os.path.join(self.download_path, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Ошибка удаления файла: {e}")
            return False

    # ---- Офлайн-кэш PDF ----

    def _cache_path_for(self, book: Book) -> str:
        """Путь файла в офлайн-кэше (тот же стабильный формат имени, что и при скачивании)."""
        pdf_url = self._convert_to_raw_url(book.pdf)
        if pdf_url.startswith('http'):
            original_filename = os.path.basename(pdf_url.split('?')[0])
        else:
            original_filename = os.path.basename(pdf_url)
        filename = self._get_book_filename(book, original_filename)
        return os.path.join(self.cache_path, filename)

    def get_cached_pdf(self, book: Book) -> str | None:
        """Возвращает путь к PDF из офлайн-кэша, если он там есть."""
        try:
            cache_file = self._cache_path_for(book)
            if os.path.exists(cache_file):
                return cache_file
        except Exception as e:
            print(f"Ошибка проверки кэша PDF: {e}")
        return None

    def ensure_cached(self, book: Book, source_path: str | None = None) -> str | None:
        """Копирует PDF книги в офлайн-кэш (если ещё нет), чтобы её можно было читать без интернета."""
        try:
            cache_file = self._cache_path_for(book)
            if os.path.exists(cache_file):
                return cache_file

            if not source_path or not os.path.exists(source_path):
                is_downloaded, source_path = self.is_book_downloaded(book)
                if not is_downloaded or not source_path:
                    return None

            os.makedirs(self.cache_path, exist_ok=True)
            shutil.copy2(source_path, cache_file)
            print(f"[Cache] PDF закэширован: {cache_file}")
            return cache_file
        except Exception as e:
            print(f"Ошибка кэширования PDF: {e}")
            return None

    def download_to_cache(self, book: Book) -> str | None:
        """Скачивает книгу прямо в офлайн-кэш и возвращает путь к файлу."""
        try:
            cached = self.get_cached_pdf(book)
            if cached:
                return cached
            return self.ensure_cached(book, self.download_book(book))
        except Exception as e:
            print(f"Ошибка скачивания в кэш: {e}")
            return None

    def is_book_downloaded(self, book: Book) -> tuple[bool, str | None]:
        """
        Проверяет, скачана ли книга, и возвращает статус и путь к файлу

        Args:
            book: Объект книги для проверки

        Returns:
            tuple: (is_downloaded: bool, filepath: Optional[str])
        """
        try:
            # Конвертируем URL в raw формат (для GitHub)
            pdf_url = self._convert_to_raw_url(book.pdf)

            # Получаем исходное имя файла из URL для использования в поиске
            original_filename = None
            if pdf_url.startswith('http'):
                original_filename = os.path.basename(pdf_url.split('?')[0])
            else:
                original_filename = os.path.basename(pdf_url)

            # Генерируем стабильное имя файла (то же самое, что при скачивании)
            filename = self._get_book_filename(book, original_filename)

            full_path = os.path.join(self.download_path, filename)

            # Проверяем, существует ли файл с новым именем
            if os.path.exists(full_path):
                return True, full_path

            # Обратная совместимость: проверяем старые варианты имён файлов
            # в случае если файлы были загружены со старой версией кода
            old_filenames = []

            # Вариант 1: исходное имя файла из URL
            if original_filename and original_filename.endswith('.pdf'):
                old_filenames.append(original_filename)

            # Вариант 2: имя на основе названия книги (старая логика)
            if book.title:
                old_filenames.append(f"{book.title}.pdf")

            # Вариант 3: имя на основе ID (очень старая логика)
            old_filenames.append(f"book_{book.id}.pdf")

            # Проверяем каждое старое имя
            for old_filename in old_filenames:
                old_path = os.path.join(self.download_path, old_filename)
                if os.path.exists(old_path):
                    # Файл найден со старым именем - возвращаем его
                    # (не переименовываем, так как может быть несколько экземпляров)
                    return True, old_path

            return False, None

        except Exception as e:
            print(f"Ошибка проверки книги: {e}")
            return False, None
