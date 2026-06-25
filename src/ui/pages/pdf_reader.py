import flet as ft
import os
import sys
import threading
import tempfile
import time
import shutil
import subprocess
from typing import Optional
from src.core.models import Book
from src.core.downloader import Downloader
from src.core.statistics_manager import stats  # 🔥 Централизованный менеджер статистики

try:
    import fitz  # pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Глобальная папка для временных файлов
TEMP_DIR = os.path.join(tempfile.gettempdir(), "nurbooks_pdf_reader")


def cleanup_temp_files():
    """Очищает все временные файлы"""
    try:
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR, ignore_errors=True)
    except Exception as e:
        print(f"Ошибка очистки временных файлов: {e}")


def _convert_github_url(url: str) -> str:
    """Конвертирует GitHub ссылку в raw-ссылку."""
    if not url:
        return url
    if "raw.githubusercontent.com" in url:
        return url
    if "github.com" in url and "/blob/" in url:
        return url.replace("/blob/", "/raw/")
    return url


class PDFReaderPage:
    """
    PDF-ридер с надёжным обновлением через файлы.
    """
    
    def __init__(self, page: ft.Page, book: Book, on_back=None, downloader: Optional[Downloader] = None, bookmarks=None, go_to_page: Optional[int] = None):
        self.page = page
        self.book = book
        self.on_back = on_back
        self.downloader = downloader or Downloader()
        self.bookmarks = bookmarks or []
        self.go_to_page = go_to_page

        # Состояние
        self.pdf_doc = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom = 1.0
        self.pdf_path: Optional[str] = None
        self.render_dir: str = ""
        
        # Блокировки
        self._render_lock = threading.Lock()
        self._stop_preload = threading.Event()

        # Создаём временную директорию
        os.makedirs(TEMP_DIR, exist_ok=True)
        self.render_dir = tempfile.mkdtemp(dir=TEMP_DIR) or ""

        # UI - ИЗОБРАЖЕНИЕ (самое важное!)
        self.page_image = ft.Image(
            src="",
            fit=ft.ImageFit.NONE,
            gapless_playback=True,  # Важно для плавной смены!
        )
        
        # Иконка-заглушка
        self.placeholder = ft.Column(
            [ft.Icon(ft.icons.MENU_BOOK, size=80, color=ft.colors.with_opacity(0.3, ft.colors.ON_SURFACE))],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        # Контейнер изображения
        self.image_stack = ft.Stack(
            [self.placeholder, self.page_image],
            alignment=ft.alignment.center,
        )

        # Loading
        self.loading_ring = ft.ProgressRing(width=40, height=40)
        self.loading_text = ft.Text("Подготовка...")
        self.progress_bar = ft.ProgressBar(width=200, bar_height=3)
        
        self.loading_column = ft.Column(
            [self.loading_ring, self.progress_bar, self.loading_text],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=15,
        )

        # Ошибка
        self.error_text = ft.Text("", color=ft.colors.ERROR, text_align=ft.TextAlign.CENTER)
        self.download_btn_big = ft.ElevatedButton(
            "Скачать книгу",
            icon=ft.icons.DOWNLOAD,
            on_click=self._download_book,
            visible=False,
        )
        
        self.error_column = ft.Column(
            [self.error_text, self.download_btn_big],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
        )

        # Оверлей
        self.overlay = ft.Container(
            content=self.loading_column,
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.colors.SURFACE,
        )

        # Навигация
        self.prev_btn = ft.IconButton(
            icon=ft.icons.ARROW_LEFT,
            on_click=self._prev_page,
            disabled=True,
        )
        self.next_btn = ft.IconButton(
            icon=ft.icons.ARROW_RIGHT,
            on_click=self._next_page,
            disabled=True,
        )
        self.zoom_label = ft.Text(f"{int(self.zoom * 100)}%")
        self.page_input = ft.TextField(
            hint_text="№",
            width=50,
            height=35,
            text_size=13,
            text_align=ft.TextAlign.CENTER,
            on_submit=self._jump_to_page,
        )
        self.total_pages_text = ft.Text(f"{self.total_pages}", size=14, weight=ft.FontWeight.BOLD)

        # Строим UI
        self.content = self._build_ui()

        # Запускаем загрузку
        threading.Thread(target=self._load_pdf, daemon=True).start()

    def _build_ui(self) -> ft.Control:
        top_bar = ft.Container(
            content=ft.Row([
                ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=self._go_back, tooltip="Назад"),
                ft.Text(self.book.title, size=16, weight=ft.FontWeight.BOLD, expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.IconButton(icon=ft.icons.STAR_BORDER, on_click=self._add_bookmark, tooltip="Закладка"),
                ft.IconButton(icon=ft.icons.ZOOM_OUT, on_click=self._zoom_out, tooltip="Уменьшить"),
                self.zoom_label,
                ft.IconButton(icon=ft.icons.ZOOM_IN, on_click=self._zoom_in, tooltip="Увеличить"),
            ]),
            padding=10,
            bgcolor=ft.colors.SURFACE_VARIANT,
        )

        scrollable_content = ft.Row(
            [
                ft.Column(
                    [self.image_stack],
                    scroll=ft.ScrollMode.AUTO,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
        )

        viewer = ft.Container(
            content=ft.Stack([scrollable_content, self.overlay], expand=True),
            expand=True,
            alignment=ft.alignment.center,
        )

        bottom_bar = ft.Container(
            content=ft.Row([
                self.prev_btn,
                ft.Container(expand=True),
                self.page_input,
                ft.Text(" / ", size=14),
                self.total_pages_text,
                ft.Container(width=10),
                ft.IconButton(
                    icon=ft.icons.SEND,
                    icon_size=16,
                    tooltip="Перейти",
                    on_click=self._jump_to_page,
                ),
                ft.Container(expand=True),
                self.next_btn,
            ], alignment=ft.MainAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=10, vertical=5),
            bgcolor=ft.colors.SURFACE_VARIANT,
        )

        return ft.Column([top_bar, viewer, bottom_bar], expand=True, spacing=0)

    def _show_loading(self, text: str = "Загрузка..."):
        """Показывает индикатор загрузки"""
        self.loading_text.value = text
        self.loading_ring.visible = True
        self.progress_bar.visible = False
        self.overlay.content = self.loading_column
        self.overlay.visible = True
        self.page_image.visible = False
        self.placeholder.visible = False
        try:
            self.page.update()
        except Exception:
            pass

    def _show_error(self, error: str, show_download: bool = False):
        """Показывает ошибку"""
        self.error_text.value = error
        self.download_btn_big.visible = show_download
        self.overlay.content = self.error_column
        self.overlay.visible = True
        self.page_image.visible = False
        try:
            self.page.update()
        except Exception:
            pass

    def _save_progress(self):
        """Сохраняет прогресс чтения в БД"""
        if self.book.id > 0 and self.pdf_doc:
            from src.core.database import Database
            db = Database()
            db.save_reading_progress(self.book.id, self.current_page + 1)

    def _show_page_image(self, image_path: str):
        """Показывает изображение страницы - ГЛАВНЫЙ МЕТОД"""
        try:
            page_rect = self.pdf_doc[self.current_page].rect if self.pdf_doc else None
            if page_rect:
                scaled_width = max(1, int(page_rect.width * self.zoom))
                scaled_height = max(1, int(page_rect.height * self.zoom))
                self.page_image.width = scaled_width
                self.page_image.height = scaled_height
                self.image_stack.width = scaled_width
                self.image_stack.height = scaled_height

            # Устанавливаем src изображения
            self.page_image.src = image_path
            self.page_image.visible = True
            self.placeholder.visible = False
            self.overlay.visible = False
            
            # Обновляем счётчик
            self.total_pages_text.value = str(self.total_pages)
            self.page_input.value = str(self.current_page + 1)
            self.prev_btn.disabled = self.current_page <= 0
            self.next_btn.disabled = self.current_page >= self.total_pages - 1
            
            # Сохраняем прогресс
            self._save_progress()
            
            # Обновляем страницу
            self.page.update()
            print(f"[PDF] Показана страница {self.current_page + 1}")
        except Exception as e:
            print(f"[PDF] Ошибка показа: {e}")

    def _load_pdf(self):
        """Загружает PDF в фоне"""
        print(f"[PDF] Загрузка: {self.book.title}")
        self._show_loading("Поиск книги...")

        if not PYMUPDF_AVAILABLE:
            self._show_error("❌ PyMuPDF не установлен!\n\npip install pymupdf")
            return

        try:
            # Ищем файл
            is_downloaded, filepath = self.downloader.is_book_downloaded(self.book)
            if not is_downloaded or not filepath or not os.path.exists(filepath):
                is_downloaded, filepath = self._find_pdf_manual()

            if is_downloaded and filepath and os.path.exists(filepath):
                self.pdf_path = filepath
                print(f"[PDF] Файл найден: {filepath}")
            else:
                self._show_error(
                    "❌ Книга не скачана!\n\nСначала скачайте книгу.",
                    show_download=True
                )
                return

            # Открываем
            self._show_loading("Открытие...")
            self.pdf_doc = fitz.open(self.pdf_path)
            self.total_pages = len(self.pdf_doc)
            print(f"[PDF] Страниц: {self.total_pages}")

            # Определяем начальную страницу (приоритет: go_to_page > сохраненный прогресс > 0)
            if self.go_to_page is not None:
                start_page = self.go_to_page - 1
            else:
                from src.core.database import Database
                saved_page = Database().get_reading_progress(self.book.id)
                start_page = (saved_page - 1) if saved_page else 0
            start_page = max(0, min(start_page, self.total_pages - 1))

            # Рендерим первую страницу и показываем
            first_page_path = self._render_page(start_page)
            if first_page_path:
                self._show_page_image(first_page_path)
            else:
                self._show_error("Ошибка рендеринга первой страницы")
                return

            # Предзагрузка
            threading.Thread(target=self._preload_pages, daemon=True).start()

        except Exception as e:
            print(f"[PDF] Ошибка: {e}")
            import traceback
            traceback.print_exc()
            self._show_error(f"Ошибка:\n{e}")

    def _find_pdf_manual(self) -> tuple:
        """Ищет PDF вручную"""
        paths = []
        
        # Downloads
        dl_dir = os.path.join(os.path.expanduser("~/Downloads"), "downloads-nurbooks")
        if os.path.exists(dl_dir):
            for f in os.listdir(dl_dir):
                if f.endswith(".pdf"):
                    paths.append(os.path.join(dl_dir, f))

        # Проект
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        for folder in ["saved_books", "pdfs"]:
            p = os.path.join(base, folder)
            if os.path.exists(p):
                for f in os.listdir(p):
                    if f.endswith(".pdf"):
                        paths.append(os.path.join(p, f))

        for path in paths:
            try:
                doc = fitz.open(path)
                count = len(doc)
                doc.close()
                if count > 0:
                    # Проверяем принадлежность книге
                    if str(self.book.id) in path or self.book.title[:15].replace(" ", "_") in path:
                        return True, path
            except Exception as e:
                print(f"[PDF] Ошибка при проверке файла {path}: {e}")
                continue

        return False, None

    def _render_page(self, page_num: int) -> Optional[str]:
        """Рендерит страницу в файл и возвращает путь"""
        if not self.pdf_doc or page_num < 0 or page_num >= self.total_pages:
            return None

        try:
            with self._render_lock:
                # Имя файла включает зум для корректного кэширования
                output_path = os.path.join(self.render_dir, f"page_{page_num}_zoom{int(self.zoom*100)}.png")

                # Если уже есть - возвращаем
                if os.path.exists(output_path):
                    return output_path

                # Рендерим
                page = self.pdf_doc[page_num]
                mat = fitz.Matrix(self.zoom, self.zoom)
                render_method = getattr(page, 'get_pixmap', None) or getattr(page, 'getPixmap', None)
                if render_method:
                    pix = render_method(matrix=mat, alpha=False)
                    pix.save(output_path)
                else:
                    raise AttributeError("No render method available in PyMuPDF")
                
                print(f"[PDF] Страница {page_num + 1} отрендерена (zoom={self.zoom})")
                return output_path

        except Exception as e:
            print(f"[PDF] Ошибка рендеринга: {e}")
            return None

    def _preload_pages(self):
        """Предзагрузка соседних страниц"""
        time.sleep(0.5)
        
        offsets = [1, 2, -1, 3, 4]
        for offset in offsets:
            if self._stop_preload.is_set():
                break
            pg = self.current_page + offset
            if 0 <= pg < self.total_pages:
                self._render_page(pg)

    def _show_page(self, page_num: int):
        """Показывает страницу (вызывается из потока)"""
        if page_num < 0 or page_num >= self.total_pages:
            return

        self.current_page = page_num
        
        # Пытаемся найти в кэше
        path = self._render_page(page_num)
        if path:
            self._show_page_image(path)
            return

        # Ошибка
        self._show_error("Ошибка рендеринга")

    def _prev_page(self, e):
        if self.current_page > 0:
            self._show_loading(f"Страница {self.current_page}...")
            threading.Thread(target=self._show_page, args=(self.current_page - 1,), daemon=True).start()
            threading.Thread(target=self._preload_pages, daemon=True).start()

    def _next_page(self, e):
        if self.current_page < self.total_pages - 1:
            self._show_loading(f"Страница {self.current_page + 2}...")
            threading.Thread(target=self._show_page, args=(self.current_page + 1,), daemon=True).start()
            threading.Thread(target=self._preload_pages, daemon=True).start()

    def _zoom_in(self, e):
        if self.zoom < 3.0:
            self.zoom = round(self.zoom + 0.25, 2)
            self._apply_zoom()

    def _zoom_out(self, e):
        if self.zoom > 0.5:
            self.zoom = round(self.zoom - 0.25, 2)
            self._apply_zoom()

    def _apply_zoom(self):
        """Применяет новый зум"""
        # Обновляем метку
        self.zoom_label.value = f"{int(self.zoom * 100)}%"
        # Показываем loading
        self._show_loading(f"Масштаб {int(self.zoom * 100)}%...")
        # Рендерим в фоне и показываем
        def render_zoomed():
            path = self._render_page(self.current_page)
            if path:
                self._show_page_image(path)
            else:
                self._show_error("Ошибка изменения масштаба")
        threading.Thread(target=render_zoomed, daemon=True).start()

    def _clear_render_cache(self):
        """Очищает кэш рендеринга"""
        try:
            if self.render_dir and os.path.exists(self.render_dir):
                for f in os.listdir(self.render_dir):
                    os.remove(os.path.join(self.render_dir, f))
        except Exception:
            pass

    def _download_book(self, e):
        """Скачивает книгу"""
        def download():
            try:
                self._show_loading("Скачивание...")
                path = self.downloader.download_book(self.book)
                from src.core.statistics_manager import stats
                stats.increment_download_count(self.book.id)
                self.book.download_count = getattr(self.book, "download_count", 0) + 1
                print(f"[PDF] Скачано: {path}")
                
                # Показываем уведомление
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Скачано: {self.book.title}"))
                self.page.snack_bar.open = True
                self.page.update()

                # Перезагружаем
                if self.pdf_doc:
                    self.pdf_doc.close()
                    
                self._load_pdf()
            except Exception as ex:
                self._show_error(f"Ошибка скачивания:\n{ex}")
        threading.Thread(target=download, daemon=True).start()

    def _go_back(self, e):
        """Возврат"""
        self._stop_preload.set()
        self._save_progress()
        if self.pdf_doc:
            try:
                self.pdf_doc.close()
            except Exception:
                pass
        self._clear_render_cache()
        if self.on_back:
            self.on_back()
    
    def _add_bookmark(self, e):
        """Добавляет закладку для текущей страницы"""
        from src.core.database import Database
        from datetime import datetime
        
        db = Database()
        
        # Проверяем, нет ли уже закладки на этой странице
        existing = [b for b in self.bookmarks if b.book_id == self.book.id and b.page_number == self.current_page + 1]
        if existing:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Закладка на странице {self.current_page + 1} уже существует", color=ft.colors.BLACK),
                bgcolor=ft.colors.AMBER
            )
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        # Добавляем закладку
        from src.core.models import Bookmark
        bookmark = Bookmark(
            id=0,
            book_id=self.book.id,
            page_number=self.current_page + 1,
            timestamp=datetime.now().isoformat()
        )
        
        if db.add_bookmark(bookmark):
            self.bookmarks.append(bookmark)
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Закладка добавлена на страницу {self.current_page + 1}"),
                bgcolor=ft.colors.GREEN
            )
        else:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Ошибка при добавлении закладки"),
                bgcolor=ft.colors.ERROR
            )
        self.page.snack_bar.open = True
        self.page.update()
    
    def _jump_to_page(self, e):
        """Переход на указанную страницу"""
        try:
            page = int(self.page_input.value)
            if page < 1 or page > self.total_pages:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Страницы {page} нет. Введите от 1 до {self.total_pages}"),
                    bgcolor=ft.colors.ERROR
                )
                self.page.snack_bar.open = True
                self.page.update()
                return
            self._show_loading(f"Страница {page}...")
            threading.Thread(target=self._show_page, args=(page - 1,), daemon=True).start()
            threading.Thread(target=self._preload_pages, daemon=True).start()
        except ValueError:
            self.page_input.value = str(self.current_page + 1)
            self.page.update()

    def build(self) -> ft.Control:
        return self.content


def on_app_exit():
    """Вызывать при выходе из приложения"""
    cleanup_temp_files()

