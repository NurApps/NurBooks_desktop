import flet as ft
import os
from typing import List
from src.core.downloader import Downloader
from src.core.notifications import NotificationManager
from src.core.storage import Storage
from src.core.models import Book
from src.core.database import Database
from datetime import datetime
import json

class MyLibraryPage:
    def __init__(self, page: ft.Page, notification_manager: NotificationManager = None, on_read_book=None):
        self.page = page
        self.notification_manager = notification_manager
        self.storage = Storage()
        self.settings = self.storage.load_settings()
        self.downloader = Downloader(download_path=self.settings.default_path)
        self.on_read_book = on_read_book  # Callback для открытия встроенной читалки
        
        self.downloaded_books: List[str] = []
        self.saved_books: List[str] = []  # Здесь будут ID сохраненных книг
        self.favorite_books: List[str] = []  # Здесь будут ID избранных книг
        self.bookmarks = []  # Список закладок (bookmark, book) из БД
        
        self._load_data()
        self.content = self._create_content()
    
    def _load_data(self):
        """Загружает данные"""
        self.downloaded_books = self.downloader.get_downloaded_books()
        # Загрузка сохраненных книг из файла
        try:
            with open("data/saved_books.json", "r") as f:
                self.saved_books = json.load(f)
        except FileNotFoundError:
            self.saved_books = []
        except Exception:
            self.saved_books = []
        
        # Загрузка избранных книг из файла
        try:
            with open("data/favorite_books.json", "r") as f:
                self.favorite_books = json.load(f)
        except FileNotFoundError:
            self.favorite_books = []
        except Exception:
            self.favorite_books = []
        
        # Загрузка закладок из базы данных
        db = Database()
        self.bookmarks = db.get_all_bookmarks_with_books()
    
    def _save_saved_books(self):
        """Сохраняет список сохраненных книг"""
        try:
            with open("data/saved_books.json", "w") as f:
                json.dump(self.saved_books, f)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    def _save_favorite_books(self):
        """Сохраняет список избранных книг"""
        try:
            with open("data/favorite_books.json", "w") as f:
                json.dump(self.favorite_books, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения избранного: {e}")
    
    def _create_downloaded_book_item(self, book: Book, filename: str) -> ft.Control:
        """Создает элемент для скачанной книги"""
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.icons.PICTURE_AS_PDF, color=ft.colors.RED, size=22),
                    bgcolor=ft.colors.RED_50,
                    border_radius=20,
                    width=40,
                    height=40,
                    alignment=ft.alignment.center,
                ),
                ft.Column([
                    ft.Text(book.title if book.id > 0 else filename, weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(
                        f"{book.author if book.id > 0 else 'Неизвестно'}  •  {self._get_file_size(filename)}",
                        size=12, color=ft.colors.ON_SURFACE_VARIANT
                    ),
                ], expand=True, spacing=2),
                ft.PopupMenuButton(
                    icon=ft.icons.MORE_VERT,
                    tooltip="Действия",
                    items=[
                        ft.PopupMenuItem(
                            content=ft.Row([
                                ft.Icon(ft.icons.MENU_BOOK, size=20),
                                ft.Text("Открыть/Читать")
                            ]),
                            on_click=lambda e: self._open_or_read_book(filename)
                        ),
                        ft.PopupMenuItem(
                            content=ft.Row([
                                ft.Icon(ft.icons.INFO, size=20),
                                ft.Text("Информация о книге")
                            ]),
                            on_click=lambda e, b=book: self._show_book_info(b) if b.id > 0 else None
                        ),
                        ft.PopupMenuItem(
                            content=ft.Row([
                                ft.Icon(ft.icons.FOLDER_OPEN, size=20),
                                ft.Text("Открыть папку")
                            ]),
                            on_click=lambda e: self._open_downloaded_book_folder(filename)
                        ),
                        ft.PopupMenuItem(
                            content=ft.Row([
                                ft.Icon(ft.icons.DELETE, size=20, color=ft.colors.RED),
                                ft.Text("Удалить", style=ft.TextStyle(color=ft.colors.RED))
                            ]),
                            on_click=lambda e: self._on_delete_downloaded_click(filename)
                        ),
                    ]
                ),
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            bgcolor=ft.colors.SURFACE,
            border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
            border_radius=12,
            margin=ft.margin.only(bottom=8)
        )
    
    def _get_file_size(self, filename: str) -> str:
        """Получает размер файла"""
        try:
            size = os.path.getsize(os.path.join(self.downloader.download_path, filename))
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size/1024:.1f} KB"
            else:
                return f"{size/(1024*1024):.1f} MB"
        except OSError:
            return "Неизвестно"

    def _find_book_by_filename(self, filename: str, books: list = None) -> Book:
        """Находит книгу по имени файла"""
        if books is None:
            books = self.storage.load_books()
        book_id_str = filename.split("_")[0]
        for book in books:
            if str(book.id) == book_id_str:
                return book
            if book.title and book.title[:30].replace(" ", "_") in filename:
                return book
        return Book(id=0, title=filename.replace(".pdf", ""), author="Неизвестно",
                     category="", year=0, description="", cover="", pdf="")

    def _show_book_info(self, book: Book):
        """Показывает информацию о книге"""
        from src.core.storage import Storage
        dlg = ft.AlertDialog(
            title=ft.Text(book.title, text_align=ft.TextAlign.CENTER),
            content=ft.Column([
                ft.Image(
                    src=book.cover if book.cover and book.cover.startswith(("http://", "https://")) else "assets/logo.png",
                    width=100, height=150, fit=ft.ImageFit.COVER, border_radius=5,
                ) if book.cover else ft.Container(height=10),
                ft.Text(f"Автор: {book.author}", text_align=ft.TextAlign.CENTER),
                ft.Text(f"Категория: {book.category}", text_align=ft.TextAlign.CENTER),
                ft.Text(f"Год: {book.year}", text_align=ft.TextAlign.CENTER) if book.year else ft.Container(),
                ft.Divider(),
                ft.Text(book.description, text_align=ft.TextAlign.JUSTIFY, size=13) if book.description else ft.Container(),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8, tight=True),
            actions=[ft.TextButton("Закрыть", on_click=lambda _: self.page.close(dlg))],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        self.page.open(dlg)
        self.page.update()
    
    def _create_my_book_item(self, book: Book) -> ft.Control:
        """Создает элемент для сохраненной книги (с кнопкой скачать)"""
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.icons.BOOKMARK, color=ft.colors.BLUE, size=22),
                    bgcolor=ft.colors.BLUE_50,
                    border_radius=20,
                    width=40,
                    height=40,
                    alignment=ft.alignment.center,
                ),
                ft.Column([
                    ft.Text(book.title, weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(f"Автор: {book.author}", size=12, color=ft.colors.GREY),
                ], expand=True, spacing=2),
                ft.ElevatedButton(
                    "Скачать",
                    icon=ft.icons.DOWNLOAD,
                    on_click=lambda e, b=book: self._download_saved_book(b),
                    style=ft.ButtonStyle(
                        bgcolor=ft.colors.PRIMARY_CONTAINER,
                    )
                ),
                ft.IconButton(
                    icon=ft.icons.DELETE,
                    tooltip="Удалить из библиотеки",
                    on_click=lambda e, bid=str(book.id): self._on_delete_saved_click(bid)
                ),
            ]),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            bgcolor=ft.colors.SURFACE,
            border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
            border_radius=12,
            margin=ft.margin.only(bottom=8)
        )

    def _download_saved_book(self, book: Book):
        """Скачивает сохраненную книгу"""
        def download():
            try:
                self.downloader.download_book(book)
                self.downloaded_books = self.downloader.get_downloaded_books()
                self.content = self._create_content()
                self.page.update()
                if self.notification_manager:
                    self.notification_manager.add_notification(
                        title="Книга скачана",
                        message=f"Книга '{book.title}' успешно скачана",
                        type="success"
                    )
            except Exception as ex:
                if self.notification_manager:
                    self.notification_manager.add_notification(
                        title="Ошибка скачивания",
                        message=f"Не удалось скачать '{book.title}': {ex}",
                        type="error"
                    )
        import threading
        threading.Thread(target=download, daemon=True).start()

    def _create_favorite_book_item(self, book_id: str) -> ft.Control:
        """Создает элемент для избранной книги"""
        books = self.storage.load_books()
        book = next((b for b in books if str(b.id) == book_id), None)
        
        if not book:
            return ft.Container()
        
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.icons.FAVORITE, color=ft.colors.RED, size=22),
                    bgcolor=ft.colors.RED_50,
                    border_radius=20,
                    width=40,
                    height=40,
                    alignment=ft.alignment.center,
                ),
                ft.Column([
                    ft.Text(book.title, weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(f"Автор: {book.author}", size=12, color=ft.colors.ON_SURFACE_VARIANT),
                ], expand=True, spacing=2),
                ft.IconButton(
                    icon=ft.icons.DELETE,
                    tooltip="Удалить из избранного",
                    on_click=lambda e, bid=book_id: self._on_delete_favorite_click(bid)
                ),
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            bgcolor=ft.colors.SURFACE,
            border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
            border_radius=12,
            margin=ft.margin.only(bottom=8)
        )
    
    def _create_bookmark_item(self, bookmark_data: tuple) -> ft.Control:
        """Создает элемент для закладки"""
        bookmark, book = bookmark_data
        
        def format_date(ts: str) -> str:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                return dt.strftime("%d.%m.%Y %H:%M")
            except:
                return ts
        
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.icons.BOOKMARK, color=ft.colors.AMBER, size=22),
                    bgcolor=ft.colors.AMBER_50,
                    border_radius=20,
                    width=40,
                    height=40,
                    alignment=ft.alignment.center,
                ),
                ft.Column([
                    ft.Text(book.title, weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(f"Автор: {book.author}", size=12, color=ft.colors.ON_SURFACE_VARIANT),
                    ft.Text(f"Страница {bookmark.page_number}", size=12, color=ft.colors.BLUE),
                    ft.Text(f"Добавлено: {format_date(bookmark.timestamp)}", size=11, color=ft.colors.OUTLINE),
                ], expand=True, spacing=1),
                ft.IconButton(
                    icon=ft.icons.OPEN_IN_NEW,
                    tooltip="Перейти к странице",
                    on_click=lambda e, b=book, p=bookmark.page_number: self._go_to_bookmark_page(b, p)
                ),
                ft.IconButton(
                    icon=ft.icons.DELETE,
                    tooltip="Удалить закладку",
                    icon_color=ft.colors.RED,
                    on_click=lambda e, bid=bookmark.id: self._delete_bookmark(bid)
                ),
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            bgcolor=ft.colors.SURFACE,
            border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
            border_radius=12,
            margin=ft.margin.only(bottom=8)
        )
    
    def _create_content(self) -> ft.Control:
        """Создает содержимое страницы"""
        return ft.Container(
            content=ft.Column([
                # Заголовок
                ft.Container(
                    content=ft.Text("Моя библиотека", size=28, weight=ft.FontWeight.BOLD),
                    padding=ft.padding.only(left=20, right=20, top=20, bottom=10)
                ),
                
                # Вкладки
                ft.Tabs(
                    selected_index=0,
                    animation_duration=300,
                    tabs=[
                        ft.Tab(
                            text="Мои книги",
                            content=self._create_my_books_tab()
                        ),
                        ft.Tab(
                            text="Избранные книги",
                            content=self._create_favorite_tab()
                        ),
                        ft.Tab(
                            text="Мои закладки",
                            content=self._create_bookmarks_tab()
                        ),
                    ],
                    expand=1,
                ),
            ]),
            expand=True
        )
    
    def _create_my_books_tab(self) -> ft.Control:
        """Создает вкладку Мои книги (скачанные + сохраненные)"""
        book_items = []

        # Сначала скачанные книги
        all_books = self.storage.load_books()
        for filename in self.downloaded_books:
            book = self._find_book_by_filename(filename, all_books)
            book_items.append(self._create_downloaded_book_item(book, filename))

        # Затем сохраненные книги, которых нет среди скачанных
        for book_id in self.saved_books:
            book = next((b for b in all_books if str(b.id) == book_id), None)
            if not book:
                continue
            is_downloaded, _ = self.downloader.is_book_downloaded(book)
            if not is_downloaded:
                book_items.append(self._create_my_book_item(book))

        if not book_items:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.FOLDER_OPEN, size=48, color=ft.colors.GREY),
                    ft.Text("Нет книг", size=16, color=ft.colors.GREY),
                    ft.Text("Скачайте или сохраните книги из каталога", size=12, color=ft.colors.GREY_600),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
                alignment=ft.alignment.center
            )

        return ft.Container(
            content=ft.Column([
                ft.Text(
                    f"Всего книг: {len(book_items)}",
                    size=14,
                    color=ft.colors.GREY
                ),
                ft.Container(
                    content=ft.Column(book_items, scroll=ft.ScrollMode.ADAPTIVE),
                    padding=10,
                    expand=True
                ),
            ]),
            padding=20,
            expand=True
        )
    
    def _create_favorite_tab(self) -> ft.Control:
        """Создает вкладку с избранными книгами"""
        if not self.favorite_books:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.FAVORITE_BORDER, size=48, color=ft.colors.GREY),
                    ft.Text("Нет избранных книг", size=16, color=ft.colors.GREY),
                    ft.Text("Добавьте книги в избранное из каталога", size=12, color=ft.colors.GREY_600),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
                alignment=ft.alignment.center
            )
        
        book_items = []
        for book_id in self.favorite_books:
            item = self._create_favorite_book_item(book_id)
            book_items.append(item)
        
        return ft.Container(
            content=ft.Column([
                ft.Text(
                    f"Избранных книг: {len(self.favorite_books)}",
                    size=14,
                    color=ft.colors.GREY
                ),
                ft.Container(
                    content=ft.Column(book_items, scroll=ft.ScrollMode.ADAPTIVE),
                    padding=10,
                    expand=True
                ),
            ]),
            padding=20,
            expand=True
        )
    
    def _create_bookmarks_tab(self) -> ft.Control:
        """Создает вкладку с закладками"""
        if not self.bookmarks:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.BOOKMARK, size=48, color=ft.colors.GREY),
                    ft.Text("Нет закладок", size=16, color=ft.colors.GREY),
                    ft.Text("Добавьте закладки при чтении книг", size=12, color=ft.colors.GREY_600),
                    ft.Text("через кнопку ★ в читалке", size=12, color=ft.colors.GREY_600),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
                alignment=ft.alignment.center
            )
        
        bookmark_items = []
        for bm_data in self.bookmarks:
            bookmark_items.append(self._create_bookmark_item(bm_data))
        
        return ft.Container(
            content=ft.Column([
                ft.Text(
                    f"Всего закладок: {len(self.bookmarks)}",
                    size=14,
                    color=ft.colors.GREY
                ),
                ft.Container(
                    content=ft.Column(bookmark_items, scroll=ft.ScrollMode.ADAPTIVE),
                    padding=10,
                    expand=True
                ),
            ]),
            padding=20,
            expand=True
        )
    
    def _go_to_bookmark_page(self, book, page_number):
        """Переходит к странице закладки - открывает читалку"""
        if self.on_read_book:
            self.on_read_book(book, page_number)
        else:
            self._open_or_read_book_for_bookmark(book, page_number)
    
    def _delete_bookmark(self, bookmark_id: int):
        """Удаляет закладку"""
        db = Database()
        if db.delete_bookmark(bookmark_id):
            # Перезагружаем данные
            self.bookmarks = db.get_all_bookmarks_with_books()
            self.content = self._create_content()
            self.page.update()
            
            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Закладка удалена",
                    message="Закладка успешно удалена",
                    type="info"
                )
        else:
            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Ошибка",
                    message="Не удалось удалить закладку",
                    type="error"
                )
    
    def _open_or_read_book(self, filename: str):
        """Открывает книгу - показывает диалог выбора читалки или открывает сразу по настройке"""
        file_path = os.path.join(self.downloader.download_path, filename)
        
        if not os.path.exists(file_path):
            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Файл не найден",
                    message=f"Файл '{filename}' не найден",
                    type="warning"
                )
            return
        
        # Получаем настройку читалки (перечитываем настройки для актуальности)
        self.settings = self.storage.load_settings()
        reader_pref = self.settings.pdf_reader
        
        if reader_pref == "builtin":
            self._open_in_builtin_reader(filename)
        elif reader_pref == "system":
            self._open_in_system_reader(file_path)
        else:
            self._show_reader_choice_dialog(filename, file_path)
    
    def _open_or_read_book_for_bookmark(self, book, page_number=None):
        """Открывает книгу для перехода по закладке"""
        # Пробуем on_read_book с page_number
        if self.on_read_book:
            self.on_read_book(book, page_number)
            return
        
        # Ищем скачанный файл
        is_downloaded, filepath = self.downloader.is_book_downloaded(book)
        
        if not is_downloaded or not filepath:
            # Ищем вручную
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            possible_paths = []
            
            nurbooks_path = os.path.join(os.path.expanduser("~/Downloads"), "downloads-nurbooks")
            if os.path.exists(nurbooks_path):
                for f in os.listdir(nurbooks_path):
                    if f.endswith('.pdf') and str(book.id) in f:
                        possible_paths.append(os.path.join(nurbooks_path, f))
            
            for folder in ["saved_books", "pdfs"]:
                p = os.path.join(base_path, folder)
                if os.path.exists(p):
                    for f in os.listdir(p):
                        if f.endswith('.pdf') and str(book.id) in f:
                            possible_paths.append(os.path.join(p, f))
            
            if possible_paths:
                filepath = possible_paths[0]
            else:
                if self.notification_manager:
                    self.notification_manager.add_notification(
                        title="Книга не найдена",
                        message=f"Книга '{book.title}' не скачана",
                        type="warning"
                    )
                return
        
        self._open_in_builtin_reader_for_book(book, filepath)
    
    def _show_reader_choice_dialog(self, filename: str, file_path: str):
        """Показывает диалог выбора читалки"""
        def on_builtin(e):
            self.page.dialog.open = False
            self.page.update()
            self._open_in_builtin_reader(filename)
        
        def on_system(e):
            self.page.dialog.open = False
            self.page.update()
            self._open_in_system_reader(file_path)
        
        def on_always_builtin(e):
            self._save_reader_preference("builtin")
            on_builtin(e)
        
        def on_always_system(e):
            self._save_reader_preference("system")
            on_system(e)
        
        display_name = filename[:40] + "..." if len(filename) > 40 else filename
        
        self.page.dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.MENU_BOOK, color=ft.colors.PRIMARY),
                ft.Text("Как открыть книгу?")
            ]),
            content=ft.Column([
                ft.Text(f"'{display_name}'", size=12, color=ft.colors.GREY),
            ], tight=True, spacing=10),
            actions=[
                ft.Column([
                    ft.ElevatedButton(
                        "Встроенная читалка",
                        icon=ft.icons.MENU_BOOK,
                        on_click=on_builtin,
                        width=250,
                        style=ft.ButtonStyle(bgcolor=ft.colors.PRIMARY_CONTAINER)
                    ),
                    ft.ElevatedButton(
                        "Системная программа",
                        icon=ft.icons.DESCRIPTION,
                        on_click=on_system,
                        width=250,
                    ),
                    ft.Divider(),
                    ft.Text("Запомнить выбор:", size=12, color=ft.colors.GREY),
                    ft.Row([
                        ft.TextButton("Всегда встроенная", on_click=on_always_builtin),
                        ft.TextButton("Всегда системная", on_click=on_always_system),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        self.page.dialog.open = True
        self.page.update()
    
    def _open_in_builtin_reader(self, filename: str):
        """Открывает книгу во встроенной читалке"""
        books = self.storage.load_books()
        book = None

        # Ищем книгу по имени файла в PDF URL
        for b in books:
            if b.pdf:
                pdf_name = b.pdf.split("/")[-1]
                if pdf_name == filename or filename in b.pdf or b.pdf.endswith(filename):
                    book = b
                    break

        # Если не нашли по PDF, ищем по названию
        if not book:
            safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in filename.replace('.pdf', ''))
            for b in books:
                if safe_title.lower() in b.title.lower() or b.title.lower() in safe_title.lower():
                    book = b
                    break

        if book and self.on_read_book:
            self.on_read_book(book)
        else:
            # Если книга не найдена в каталоге, создаем временный объект
            file_path = os.path.join(self.downloader.download_path, filename)
            if os.path.exists(file_path):
                from src.core.models import Book
                temp_book = Book(
                    id=0,
                    title=filename.replace('.pdf', ''),
                    author="Неизвестно",
                    category="Локальные файлы",
                    year=2024,
                    description="Локальный PDF файл",
                    cover="",
                    pdf=file_path
                )
                if self.on_read_book:
                    self.on_read_book(temp_book)
            else:
                self._open_in_system_reader(file_path)
    
    def _open_in_builtin_reader_for_book(self, book, filepath):
        """Открывает книгу во встроенной читалке с передачей пути"""
        from src.core.models import Book
        temp_book = Book(
            id=book.id,
            title=book.title,
            author=book.author,
            category=book.category,
            year=book.year,
            description=book.description,
            cover=book.cover,
            pdf=filepath
        )
        if self.on_read_book:
            self.on_read_book(temp_book)
    
    def _open_in_system_reader(self, file_path: str):
        """Открывает файл системной программой"""
        try:
            if os.path.exists(file_path):
                os.startfile(file_path) if os.name == 'nt' else os.system(f'xdg-open "{file_path}"')
        except Exception as e:
            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Ошибка открытия",
                    message=f"Не удалось открыть файл: {e}",
                    type="error"
                )
    
    def _save_reader_preference(self, reader_type: str):
        """Сохраняет предпочтение читалки"""
        self.settings.pdf_reader = reader_type
        self.storage.save_settings(self.settings)
        
        reader_name = "встроенная" if reader_type == "builtin" else "системная"
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(f"По умолчанию: {reader_name} читалка"),
            action="OK",
            duration=2000
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def _open_downloaded_book_folder(self, filename: str):
        """Открывает папку со скачанной книгой"""
        try:
            file_path = os.path.join(self.downloader.download_path, filename)
            if os.path.exists(file_path):
                folder_path = os.path.dirname(os.path.abspath(file_path))
                os.startfile(folder_path) if os.name == 'nt' else os.system(f'xdg-open "{folder_path}"')
            else:
                if self.notification_manager:
                    self.notification_manager.add_notification(
                        title="Файл не найден",
                        message=f"Файл '{filename}' не найден",
                        type="warning"
                    )
        except Exception as e:
            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Ошибка открытия папки",
                    message=f"Не удалось открыть папку: {e}",
                    type="error"
                )

    def _close_delete_dialog(self, e):
        """Закрывает диалог подтверждения удаления"""
        self.page.dialog.open = False
        self.page.update()

    def _on_delete_downloaded_click(self, filename: str):
        """Удаляет скачанную книгу"""
        def confirm_delete(e):
            if self.downloader.delete_book(filename):
                self.downloaded_books = [f for f in self.downloaded_books if f != filename]
                self.content = self._create_content()
                self.page.update()

                if self.notification_manager:
                    self.notification_manager.add_notification(
                        title="Книга удалена",
                        message=f"Файл '{filename}' удален",
                        type="info"
                    )

            self.page.dialog.open = False
            self.page.update()

        self.page.dialog = ft.AlertDialog(
            title=ft.Text("Подтверждение удаления"),
            content=ft.Text(f"Вы уверены, что хотите удалить файл '{filename}'?"),
            actions=[
                ft.TextButton("Отмена", on_click=self._close_delete_dialog),
                ft.TextButton("Удалить", on_click=confirm_delete, style=ft.ButtonStyle(color=ft.colors.RED)),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def _on_delete_saved_click(self, book_id: str):
        """Удаляет книгу из сохраненных"""
        self.saved_books = [bid for bid in self.saved_books if bid != book_id]
        self._save_saved_books()
        self.content = self._create_content()
        self.page.update()
        
        if self.notification_manager:
            self.notification_manager.add_notification(
                title="Книга удалена",
                message="Книга удалена из вашей библиотеки",
                type="info"
            )

    def _on_delete_favorite_click(self, book_id: str):
        """Удаляет книгу из избранных"""
        self.favorite_books = [bid for bid in self.favorite_books if bid != book_id]
        self._save_favorite_books()
        self.content = self._create_content()
        self.page.update()
        
        if self.notification_manager:
            self.notification_manager.add_notification(
                title="Удалено из избранного",
                message="Книга удалена из списка избранных",
                type="info"
            )
    
    def build(self) -> ft.Control:
        """Возвращает содержимое страницы"""
        return self.content