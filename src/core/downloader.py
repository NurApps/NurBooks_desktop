import os
import shutil
import sys

from src.config import BASE_PATH, DEFAULT_DATA_PATH, DEFAULT_PDFS_PATH, NURBOOKS_DOWNLOADS_PATH
from src.core.models import Book
from src.core.utils import (
    convert_github_url,
    download_to_file,
    format_file_size,
    safe_filename,
    safe_path_within,
    validate_pdf,
)


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
        return convert_github_url(url)

    def _get_book_filename(self, book: Book, original_filename: str = None) -> str:
        """Генерирует безопасное стабильное имя файла на основе ID книги.

        Название/имя из URL не может содержать путь, ``..`` или опасные
        символы — иначе книга с враждебным title писала бы вне папки загрузок.
        """
        candidate = ""
        if original_filename and str(original_filename).lower().endswith(".pdf"):
            candidate = os.path.splitext(str(original_filename))[0]
        elif book.title:
            candidate = str(book.title)

        clean_name = safe_filename(candidate, max_length=40)
        if not clean_name:
            return f"{int(book.id)}.pdf"
        return f"{int(book.id)}_{clean_name}.pdf"

    def _resolve_local_source(self, pdf_path: str) -> str | None:
        """Разрешает локальный PDF только внутри известных каталогов приложения."""
        raw = str(pdf_path or "")
        if raw.startswith(("\\\\", "//")):
            return None

        candidates = []
        if os.path.isabs(raw):
            candidates.append(raw)
        else:
            candidates.append(os.path.join(BASE_PATH, raw))
            candidates.append(os.path.join(os.getcwd(), raw))
            candidates.append(os.path.join(DEFAULT_PDFS_PATH, os.path.basename(raw)))

        allowed_roots = [DEFAULT_PDFS_PATH, os.path.join(DEFAULT_DATA_PATH, "pdf_cache")]
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            allowed_roots.append(os.path.join(meipass, "pdfs"))

        for candidate in candidates:
            real = os.path.realpath(candidate)
            if not os.path.isfile(real):
                continue
            for root in allowed_roots:
                root_real = os.path.realpath(root)
                try:
                    if os.path.commonpath([root_real, real]) == root_real:
                        return real
                except ValueError:
                    continue
        return None

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

            full_path = safe_path_within(save_path, filename)

            # Если книга уже скачана
            if os.path.exists(full_path):
                return full_path

            # Скачиваем книгу
            if pdf_url.startswith(("http://", "https://")):
                if pdf_url.startswith("http://"):
                    raise ValueError("небезопасная ссылка: разрешён только https")
                download_to_file(pdf_url, full_path, timeout=60)
                if not validate_pdf(full_path):
                    os.remove(full_path)
                    raise ValueError("скачанный файл не является PDF")
            else:
                source_path = self._resolve_local_source(pdf_url)
                if not source_path:
                    raise FileNotFoundError(f"Файл книги не найден: {pdf_url}")
                shutil.copy2(source_path, full_path)
                if not validate_pdf(full_path):
                    os.remove(full_path)
                    raise ValueError("локальный файл не является PDF")

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
        """Удалить скачанную книгу только внутри папки загрузок."""
        try:
            file_path = safe_path_within(self.download_path, filename)
            if os.path.isfile(file_path):
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
        return safe_path_within(self.cache_path, filename)

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

            try:
                full_path = safe_path_within(self.download_path, filename)
            except ValueError:
                return False, None

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
                safe_name = safe_filename(old_filename)
                if not safe_name:
                    continue
                try:
                    old_path = safe_path_within(self.download_path, safe_name)
                except ValueError:
                    continue
                if os.path.exists(old_path):
                    # Файл найден со старым именем - возвращаем его
                    # (не переименовываем, так как может быть несколько экземпляров)
                    return True, old_path

            return False, None

        except Exception as e:
            print(f"Ошибка проверки книги: {e}")
            return False, None
