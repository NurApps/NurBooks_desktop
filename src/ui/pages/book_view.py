import os

import flet as ft

from src.core.downloader import Downloader
from src.core.logger import get_logger
from src.core.models import Book
from src.core.notifications import NotificationManager
from src.core.statistics_manager import stats  # 🔥 Централизованный менеджер статистики
from src.core.storage import Storage

logger = get_logger(__name__)

class BookViewPage:
    def __init__(self, page: ft.Page, book: Book,
                 notification_manager: NotificationManager | None = None,
                 cart_widget = None,
                 on_back=None, on_read=None):
        self.page = page
        self.book = book
        self.notification_manager = notification_manager
        self.cart_widget = cart_widget
        self.on_back = on_back
        self.on_read = on_read
        self.storage = Storage()
        self.settings = self.storage.load_settings()
        self.downloader = Downloader(download_path=self.settings.default_path)

        # Загружаем список избранных книг
        from src.core.favorites import favorites
        self.favorites_manager = favorites
        self.favorite_books = self.favorites_manager.get_favorites()

        # Загружаем вишлист «Хочу прочитать»
        from src.core.wishlist import wishlist
        self.wishlist_manager = wishlist
        self.wishlist_books = self.wishlist_manager.get_wishlist()

        # Оценки и отзывы
        self.ratings_data = {"average": 0, "count": 0, "distribution": {}, "userRating": None, "reviews": []}
        self.ratings_container = ft.Container(
            content=ft.Row([ft.ProgressRing(width=18, height=18), ft.Text("Загрузка оценок...", size=13)],
                           spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=10,
        )
        self._load_ratings_async()

        # 🔥 NEW: увеличиваем просмотры сразу при открытии страницы
        self._record_book_view()

        # Создаем кнопку избранного с правильным состоянием
        self.favorite_button = self._create_favorite_button()
        self.wishlist_button = self._create_wishlist_button()

        # Проверяем скачана ли книга
        is_downloaded, _ = self._find_downloaded_file()

        # Создаем кнопки действий
        self.download_button = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.icons.DOWNLOAD),
                ft.Text("Скачать книгу"),
            ]),
            on_click=self._on_download_click,
            style=ft.ButtonStyle(padding=20),
            expand=True
        )

        # Кнопка "Читать" - видима только если книга скачана
        self.read_button = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.icons.MENU_BOOK),
                ft.Text("Читать"),
            ]),
            on_click=self._on_read_click,
            style=ft.ButtonStyle(padding=20),
            expand=True,
            visible=is_downloaded
        )

        # Кнопка "Инфо" - видима только если книга НЕ скачана
        self.info_button = ft.OutlinedButton(
            content=ft.Row([
                ft.Icon(ft.icons.INFO),
                ft.Text("Инфо"),
            ]),
            on_click=self._on_info_click,
            style=ft.ButtonStyle(padding=20),
            expand=True,
            visible=not is_downloaded
        )

        self.content = self._create_content()

    def _record_book_view(self):
        """Записывает факт просмотра книги (атомарно, в одной транзакции)"""
        try:
            # Обновляем счётчик в базе данных
            from src.core.statistics_manager import stats
            success = stats.increment_view_count(self.book.id)
            if success:
                # Обновляем локальную копию
                self.book.view_count = getattr(self.book, "view_count", 0) + 1
                logger.info(f"Записан просмотр книги ID={self.book.id} (общий счётчик: {self.book.view_count})")
            else:
                logger.warning(f"Не удалось записать просмотр книги ID={self.book.id}")
        except Exception as e:
            logger.error(f"Ошибка при записи просмотра книги: {e}", exc_info=True)

    def _load_favorite_books(self) -> list:
        """Загружает список избранных книг"""
        return self.favorites_manager.get_favorites()

    def _save_favorite_books(self):
        """Сохраняет список избранных книг"""
        pass

    def _find_downloaded_file(self) -> tuple[bool, str]:
        """
        Ищет скачанный файл книги в нескольких местах.
        Returns: (is_downloaded, filepath)
        """
        # Сначала пробуем стандартный метод
        is_downloaded, filepath = self.downloader.is_book_downloaded(self.book)
        if is_downloaded and filepath and os.path.exists(filepath):
            return True, filepath

        # Ищем вручную в разных папках
        possible_paths = []

        # 1. Папка downloads-nurbooks
        nurbooks_path = os.path.join(os.path.expanduser("~/Downloads"), "downloads-nurbooks")
        if os.path.exists(nurbooks_path):
            for f in os.listdir(nurbooks_path):
                if f.endswith('.pdf'):
                    if str(self.book.id) in f or self.book.title.replace(' ', '_')[:20] in f:
                        possible_paths.append(os.path.join(nurbooks_path, f))

        # 2. Папка saved_books
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        saved_path = os.path.join(base_path, "saved_books")
        if os.path.exists(saved_path):
            for f in os.listdir(saved_path):
                if f.endswith('.pdf'):
                    if str(self.book.id) in f or self.book.title.replace(' ', '_')[:20] in f:
                        possible_paths.append(os.path.join(saved_path, f))

        # 3. Папка pdfs
        pdfs_path = os.path.join(base_path, "pdfs")
        if os.path.exists(pdfs_path):
            for f in os.listdir(pdfs_path):
                if f.endswith('.pdf'):
                    if str(self.book.id) in f or self.book.title.replace(' ', '_')[:20] in f:
                        possible_paths.append(os.path.join(pdfs_path, f))

        # Проверяем найденные файлы
        for path in possible_paths:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return True, path

        return False, ""

    def _is_book_in_favorites(self) -> bool:
        """Проверяет, есть ли книга в избранном"""
        return self.favorites_manager.is_favorite(str(self.book.id))

    def _create_favorite_button(self) -> ft.IconButton:
        """Создает кнопку избранного с правильным состоянием"""
        is_favorite = self._is_book_in_favorites()
        return ft.IconButton(
            icon=ft.icons.FAVORITE if is_favorite else ft.icons.FAVORITE_BORDER,
            icon_color=ft.colors.AMBER if is_favorite else None,
            tooltip="В избранное" if not is_favorite else "Удалить из избранного",
            on_click=self._on_favorite_click,
            height=40,
            width=40
        )

    def _toggle_favorite_button(self):
        """Переключает состояние кнопки избранного"""
        is_favorite = self._is_book_in_favorites()
        self.favorite_button.icon = ft.icons.FAVORITE if is_favorite else ft.icons.FAVORITE_BORDER
        self.favorite_button.icon_color = ft.colors.AMBER if is_favorite else None
        self.favorite_button.tooltip = "В избранное" if not is_favorite else "Удалить из избранного"
        self.page.update()

    def _is_book_in_wishlist(self) -> bool:
        """Проверяет, есть ли книга в вишлисте"""
        return self.wishlist_manager.is_in_wishlist(str(self.book.id))

    def _create_wishlist_button(self) -> ft.IconButton:
        """Создает кнопку «Хочу прочитать» с правильным состоянием"""
        in_wishlist = self._is_book_in_wishlist()
        return ft.IconButton(
            icon=ft.icons.PLAYLIST_ADD_CHECK if in_wishlist else ft.icons.PLAYLIST_ADD,
            icon_color=ft.colors.PRIMARY if in_wishlist else None,
            tooltip="Удалить из «Хочу прочитать»" if in_wishlist else "Хочу прочитать",
            on_click=self._on_wishlist_click,
            height=40,
            width=40
        )

    def _toggle_wishlist_button(self):
        """Переключает состояние кнопки вишлиста"""
        in_wishlist = self._is_book_in_wishlist()
        self.wishlist_button.icon = ft.icons.PLAYLIST_ADD_CHECK if in_wishlist else ft.icons.PLAYLIST_ADD
        self.wishlist_button.icon_color = ft.colors.PRIMARY if in_wishlist else None
        self.wishlist_button.tooltip = "Удалить из «Хочу прочитать»" if in_wishlist else "Хочу прочитать"
        self.page.update()

    def _create_content(self) -> ft.Control:
        """Создает содержимое страницы книги"""
        # Проверяем, скачана ли книга (уже проверено в __init__)
        # Кнопки read_button и info_button уже имеют правильное visible состояние

        return ft.Container(
            content=ft.Column([
                # Кнопка назад и заголовок
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.icons.ARROW_BACK,
                            on_click=self._on_back_click,
                            tooltip="Назад к каталогу"
                        ),
                        ft.Text("Просмотр книги", size=20, weight=ft.FontWeight.BOLD),
                                                ft.Container(expand=True),
                    ]),
                    padding=ft.padding.only(left=20, right=20, top=20, bottom=10)
                ),

                ft.Divider(),

                # Основная информация о книге
                ft.Container(
                    content=ft.Row([
                        # Обложка и быстрые действия
                        ft.Container(
                            content=ft.Column([
                                # Обложка
                                ft.Container(
                                    content=ft.Image(
                                        src=self.book.cover if self.book.cover else "assets/logo.png",
                                        width=300,
                                        height=400,
                                        fit=ft.ImageFit.COVER,
                                        border_radius=ft.border_radius.all(10),
                                        error_content=ft.Icon(ft.icons.BOOK, size=100)
                                    ),
                                    margin=ft.margin.only(bottom=20)
                                ),

                                # Быстрые кнопки под обложкой
                                ft.Row([
                                    ft.ElevatedButton(
                                        "В корзину",
                                        icon=ft.icons.ADD_SHOPPING_CART,
                                        on_click=self._on_add_to_cart_click,
                                        expand=True,
                                        height=40
                                    ),
                                    self.favorite_button,
                                    self.wishlist_button,
                                ]),
                            ], spacing=10),
                            width=350,
                            margin=ft.margin.only(right=30)
                        ),

                        # Детальная информация
                        ft.Container(
                            content=ft.Column([
                                # Заголовок и автор
                                ft.Text(


                                    self.book.title,
                                    size=28,
                                    weight=ft.FontWeight.BOLD,
                                    max_lines=3,
                                    overflow=ft.TextOverflow.ELLIPSIS
                                ),
                                ft.Text(


                                    f"Автор: {self.book.author}",
                                    size=18,
                                    color=ft.colors.PRIMARY
                                ),

                                ft.Divider(),

                                # Метки
                                ft.Row([
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Icon(ft.icons.CATEGORY, size=16),
                                            ft.Text(self.book.category, size=14),
                                        ]),
                                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                                        bgcolor=ft.colors.PRIMARY_CONTAINER,
                                        border_radius=20
                                    ),
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Icon(ft.icons.CALENDAR_TODAY, size=16),
                                            ft.Text(str(self.book.year), size=14),
                                        ]),
                                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                                        bgcolor=ft.colors.SECONDARY_CONTAINER,
                                        border_radius=20
                                    ),
                                    ft.Container(
                                        content=ft.Row([
                                            ft.Icon(ft.icons.PICTURE_AS_PDF, size=16),
                                            ft.Text(self.book.file_size or "Неизвестно", size=14),
                                        ]),
                                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                                        bgcolor=ft.colors.TERTIARY_CONTAINER,
                                        border_radius=20
                                    ),
                                ], spacing=10, wrap=True),

                                # Описание
                                ft.Container(
                                    content=ft.Column([
                                        ft.Text("Описание", size=20, weight=ft.FontWeight.BOLD),
                                        ft.Container(
                                            content=ft.Text(
                                                self.book.description,
                                                size=14,
                                                text_align=ft.TextAlign.JUSTIFY
                                            ),
                                            padding=10,
                                            bgcolor=ft.colors.SURFACE_VARIANT,
                                            border_radius=8
                                        ),
                                        # Метрики
                                        ft.Row([
                                            ft.Text(
                                                f"Просмотры: {getattr(self.book, 'view_count', 0)}",
                                                size=14,
                                                color=ft.colors.PRIMARY
                                            ),
                                            ft.Container(width=20),
                                            ft.Icon(ft.icons.DOWNLOAD_OUTLINED, size=16),
                                            ft.Text(
                                                f"Скачивания: {getattr(self.book, 'download_count', 0)}",
                                                size=14,
                                                color=ft.colors.PRIMARY
                                            ),
                                        ], alignment=ft.MainAxisAlignment.CENTER),
                                    ], spacing=10),
                                    padding=ft.padding.only(top=20)
                                ),

                                # Оценки и отзывы
                                self.ratings_container,

                                # Кнопки основных действий
                                ft.Container(
                                    content=ft.Row([
                                        self.download_button,
                                        self.read_button,
                                        self.info_button,
                                        ft.OutlinedButton(
                                            content=ft.Row([
                                                ft.Icon(ft.icons.BOOKMARK_ADD),
                                                ft.Text("В библиотеку"),
                                            ]),
                                            on_click=self._on_save_click,
                                            style=ft.ButtonStyle(padding=20),
                                            expand=True
                                        ),
                                    ], spacing=20),
                                    padding=ft.padding.only(top=30)
                                ),

                                # Дополнительная информация
                                ft.Container(
                                    content=ft.ExpansionTile(
                                        title=ft.Text("Дополнительная информация"),
                                        controls=[
                                            ft.DataTable(
                                                columns=[
                                                    ft.DataColumn(ft.Text("Параметр")),
                                                    ft.DataColumn(ft.Text("Значение")),
                                                ],
                                                rows=[
                                                    ft.DataRow(cells=[
                                                        ft.DataCell(ft.Text("ID книги")),
                                                        ft.DataCell(ft.Text(str(self.book.id))),
                                                    ]),
                                                    ft.DataRow(cells=[
                                                        ft.DataCell(ft.Text("Количество страниц")),
                                                        ft.DataCell(ft.Text(str(self.book.pages or "Неизвестно"))),
                                                    ]),
                                                    ft.DataRow(cells=[
                                                        ft.DataCell(ft.Text("Статус")),
                                                        ft.DataCell(
                                                            ft.Text(
                                                                "Доступно для скачивания",
                                                                color=ft.colors.GREEN
                                                            )
                                                        ),
                                                    ]),
                                                ],
                                            ),
                                        ],
                                    ),
                                    padding=ft.padding.only(top=20)
                                ),
                            ], spacing=15),
                            expand=True
                        ),
                    ]),
                    padding=ft.padding.all(30)
                ),

                # Рекомендуемые книги (если есть)
                self._create_recommendations_section(),

            ], scroll=ft.ScrollMode.AUTO),
            expand=True


                )

    def _on_read_click(self, e):
        """Обработчик кнопки 'Читать' - проверяет скачивание и показывает диалог выбора читалки"""
        # Проверяем, скачана ли книга
        is_downloaded, filepath = self.downloader.is_book_downloaded(self.book)

        # Если не найдено, пробуем искать вручную
        if not is_downloaded or not filepath:
            is_downloaded, filepath = self._find_downloaded_file()

        if not is_downloaded or not filepath:
            # Книга не скачана - показываем уведомление
            self._show_download_required_dialog()
            return

        # Перечитываем настройки для актуальности
        self.settings = self.storage.load_settings()

        # Книга скачана - показываем диалог выбора читалки или открываем сразу
        if self.settings.pdf_reader == "builtin":
            # Открыть во встроенной читалке
            if self.on_read:
                self.on_read(self.book)
        elif self.settings.pdf_reader == "system":
            # Открыть в системной читалке
            self._open_downloaded_book(filepath)
        else:
            # Показать диалог выбора
            self._show_reader_choice_dialog(filepath)

    def _show_download_required_dialog(self):
        """Показывает диалог о необходимости скачивания"""
        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.DOWNLOAD, color=ft.colors.PRIMARY),
                ft.Text("Требуется скачивание")
            ]),
            content=ft.Column([
                ft.Text("Чтобы читать книгу, её нужно сначала скачать."),
                ft.Text(f"Книга: {self.book.title}", weight=ft.FontWeight.BOLD),
                ft.Text(f"Размер: {self.book.file_size or 'Неизвестно'}"),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: self.page.close(dlg)),
                ft.ElevatedButton(
                    "Скачать",
                    icon=ft.icons.DOWNLOAD,
                    on_click=lambda e: (self.page.close(dlg), self._on_download_click(e))
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)

    def _show_reader_choice_dialog(self, filepath: str):
        """Показывает диалог выбора читалки"""
        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.MENU_BOOK, color=ft.colors.PRIMARY),
                ft.Text("Выберите читалку")
            ]),
            content=ft.Column([
                ft.Text("Как вы хотите открыть книгу?", size=16),
                ft.Text(f"'{self.book.title[:30]}...'", size=12, color=ft.colors.GREY),
            ], tight=True, spacing=10),
            actions=[
                ft.Column([
                    ft.ElevatedButton(
                        "📖 Встроенная читалка",
                        on_click=lambda e: (self.page.close(dlg), self.on_read(self.book) if self.on_read else None),
                        width=250,
                        style=ft.ButtonStyle(
                            bgcolor=ft.colors.PRIMARY_CONTAINER,
                        )
                    ),
                    ft.ElevatedButton(
                        "📄 Системная программа",
                        on_click=lambda e: (self.page.close(dlg), self._open_downloaded_book(filepath)),
                        width=250,
                    ),
                    ft.Divider(),
                    ft.Text("Запомнить выбор:", size=12, color=ft.colors.GREY),
                    ft.Row([
                        ft.TextButton(
                            "Всегда встроенная",
                            on_click=lambda e: (self._save_reader_preference("builtin"), self.page.close(dlg), self.on_read and self.on_read(self.book)),
                            icon=ft.icons.STAR_BORDER,
                        ),
                        ft.TextButton(
                            "Всегда системная",
                            on_click=lambda e: (self._save_reader_preference("system"), self.page.close(dlg), self._open_downloaded_book(filepath)),
                            icon=ft.icons.STAR_BORDER,
                        ),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        self.page.open(dlg)

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

    def _close_dialog(self, dlg=None):
        """Закрывает диалог"""
        if dlg:
            self.page.close(dlg)

    def _create_recommendations_section(self) -> ft.Control:
        """Создает раздел с рекомендованными книгами"""
        # TODO: Добавить логику получения рекомендаций на основе категории/автора
        return ft.Container(
            content=ft.Text(
                "Рекомендации скоро появятся!",
                size=14,
                color=ft.colors.GREY,
                text_align=ft.TextAlign.CENTER,
            ),
            padding=20,
            alignment=ft.alignment.center,
        )

    def _on_back_click(self, e):
        """Обработчик кнопки назад"""
        if self.on_back:
            self.on_back()

    def _on_download_click(self, e):
        """Обработчик скачивания книги"""
        # Сначала проверяем, не скачана ли книга уже
        is_downloaded, filepath = self.downloader.is_book_downloaded(self.book)

        # Если не найдено, пробуем искать вручную
        if not is_downloaded or not filepath:
            is_downloaded, filepath = self._find_downloaded_file()

        if is_downloaded and filepath:
            self._update_read_button_visibility(True)
            # Книга уже скачана, предлагаем открыть или открыть папку
            self.page.snack_bar = ft.SnackBar(
                content=ft.Row([
                    ft.Icon(ft.icons.INFO, color=ft.colors.BLUE),
                    ft.Text(f"Книга '{self.book.title}' уже скачана", expand=True),
                    ft.TextButton(
                        "Открыть",
                        on_click=lambda e: self._open_downloaded_book(filepath)
                    ),
                    ft.TextButton(
                        "Открыть папку",
                        on_click=lambda e: self._open_download_folder()
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                action="OK",
                bgcolor=ft.colors.SURFACE_VARIANT
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        try:
            filepath = self.downloader.download_book(self.book)
            stats.increment_download_count(self.book.id)
            self.book.download_count = getattr(self.book, "download_count", 0) + 1

            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Книга скачана",
                    message=f"Книга '{self.book.title}' успешно скачана",
                    type="success"
                )

            # Показать сообщение об успехе с кнопкой открытия папки
            self.page.snack_bar = ft.SnackBar(
                content=ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN),
                    ft.Text(f"Книга '{self.book.title}' успешно скачана", expand=True),
                    ft.TextButton(
                        "Открыть папку",
                        on_click=lambda e: self._open_download_folder()
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                action="OK",
                duration=5000
            )
            self.page.snack_bar.open = True
            self.page.update()

            # Обновляем видимость кнопки "Читать"
            self._update_read_button_visibility(True)

        except Exception as e:
            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Ошибка скачивания",
                    message=str(e),
                    type="error"
                )

            self.page.snack_bar = ft.SnackBar(
                content=ft.Row([
                    ft.Icon(ft.icons.ERROR, color=ft.colors.RED),
                    ft.Text(f"Ошибка при скачивании: {str(e)}", expand=True),
                ]),
                bgcolor=ft.colors.ERROR_CONTAINER
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _update_read_button_visibility(self, is_downloaded: bool):
        """Обновляет видимость кнопок после скачивания"""
        if self.read_button:
            self.read_button.visible = is_downloaded
        if self.info_button:
            self.info_button.visible = not is_downloaded
        if self.download_button:
            self.download_button.disabled = is_downloaded
            if is_downloaded:
                self.download_button.content = ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE),
                    ft.Text("Скачано"),
                ])
            else:
                self.download_button.content = ft.Row([
                    ft.Icon(ft.icons.DOWNLOAD),
                    ft.Text("Скачать книгу"),
                ])
        self.page.update()

    def _on_info_click(self, e):
        """Обработчик кнопки 'Инфо' - показывает информацию о том как читать"""
        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.INFO, color=ft.colors.PRIMARY),
                ft.Text("Как читать книгу")
            ]),
            content=ft.Column([
                ft.Text("Чтобы читать книгу, её нужно сначала скачать.", size=16),
                ft.Divider(),
                ft.Text("После скачивания вы сможете читать:", weight=ft.FontWeight.BOLD),
                ft.Column([
                    ft.Row([
                        ft.Icon(ft.icons.CHECK, color=ft.colors.GREEN, size=16),
                        ft.Text("Во встроенной читалке NurBooks")
                    ]),
                    ft.Row([
                        ft.Icon(ft.icons.CHECK, color=ft.colors.GREEN, size=16),
                        ft.Text("В системной программе для PDF")
                    ]),
                ], spacing=5),
                ft.Divider(),
                ft.Text("Нажмите кнопку 'Скачать книгу' чтобы начать.", weight=ft.FontWeight.BOLD),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Понятно", on_click=lambda e: self._close_dialog()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)

    def _open_downloaded_book(self, filepath: str):
        """Открывает скачанную книгу"""
        try:
            if os.path.exists(filepath):
                os.startfile(filepath) if os.name == 'nt' else os.system(f'xdg-open "{filepath}"')
        except Exception as e:
            logger.error(f"Ошибка открытия файла '{filepath}': {e}", exc_info=True)

    def _open_download_folder(self):
        """Открывает папку со скачанными файлами"""
        try:
            download_path = self.downloader.download_path
            if os.path.exists(download_path):
                os.startfile(download_path) if os.name == 'nt' else os.system(f'xdg-open "{download_path}"')
        except Exception as e:
            logger.error(f"Ошибка открытия папки '{download_path}': {e}", exc_info=True)

    def _on_save_click(self, e):
        """Обработчик сохранения в библиотеку"""
        # Сохраняем книгу в JSON файл
        try:
            import json
            saved_books_file = "data/saved_books.json"

            # Загружаем существующие сохраненные книги
            saved_books = []
            if os.path.exists(saved_books_file):
                with open(saved_books_file, encoding='utf-8') as f:
                    saved_books = json.load(f)

            # Проверяем, нет ли уже этой книги
            if str(self.book.id) not in saved_books:
                saved_books.append(str(self.book.id))

                # Сохраняем обратно
                with open(saved_books_file, 'w', encoding='utf-8') as f:
                    json.dump(saved_books, f, ensure_ascii=False, indent=2)

                if self.notification_manager:
                    self.notification_manager.add_notification(
                        title="Книга добавлена",
                        message=f"Книга '{self.book.title}' добавлена в вашу библиотеку",
                        type="success"
                    )

                self.page.snack_bar = ft.SnackBar(
                    content=ft.Row([
                        ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN),
                        ft.Text(f"Книга '{self.book.title}' добавлена в вашу библиотеку!", expand=True),
                    ]),
                    action="OK"
                )
            else:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("Эта книга уже в вашей библиотеке"),
                    action="OK"
                )

            self.page.snack_bar.open = True
            self.page.update()

        except Exception as e:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Ошибка при сохранении: {str(e)}"),
                bgcolor=ft.colors.ERROR
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _on_add_to_cart_click(self, e):
        """Добавляет книгу в корзину"""
        if self.cart_widget and self.cart_widget.add_book(self.book):
            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Книга добавлена",
                    message=f"Книга '{self.book.title}' добавлена в корзину",
                    type="success"
                )

            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Книга '{self.book.title}' добавлена в корзину!"),
                action="OK"
            )
        else:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Эта книга уже в корзине"),
                action="OK"
            )

        self.page.snack_bar.open = True
        self.page.update()

    def _on_favorite_click(self, e):
        """Переключает статус избранного для книги"""
        try:
            book_id = str(self.book.id)

            # Проверяем, есть ли книга уже в избранном
            if self.favorites_manager.is_favorite(book_id):
                # Удаляем из избранного
                self.favorites_manager.remove(book_id)
                message = f"Книга '{self.book.title}' удалена из избранного"
            else:
                # Добавляем в избранное
                self.favorites_manager.add(book_id)
                message = f"Книга '{self.book.title}' добавлена в избранное"

            # Обновляем локальный список и кнопку
            self.favorite_books = self.favorites_manager.get_favorites()
            self._toggle_favorite_button()

            # Показываем сообщение
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(message),
                action="OK"
            )
            self.page.snack_bar.open = True
            self.page.update()

        except Exception as e:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Ошибка при работе с избранным: {str(e)}"),
                bgcolor=ft.colors.ERROR
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _on_wishlist_click(self, e):
        """Переключает статус «Хочу прочитать» для книги"""
        try:
            book_id = str(self.book.id)
            if self.wishlist_manager.is_in_wishlist(book_id):
                self.wishlist_manager.remove(book_id)
                message = f"Книга '{self.book.title}' убрана из «Хочу прочитать»"
            else:
                self.wishlist_manager.add(book_id)
                message = f"Книга '{self.book.title}' добавлена в «Хочу прочитать»"
            self.wishlist_books = self.wishlist_manager.get_wishlist()
            self._toggle_wishlist_button()
            self.page.snack_bar = ft.SnackBar(content=ft.Text(message), action="OK")
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Ошибка при работе с вишлистом: {str(ex)}"),
                bgcolor=ft.colors.ERROR
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _load_ratings_async(self):
        """Фоново загружает оценки и отзывы книги."""
        def _load():
            try:
                from src.core.firebase_client import firebase_client
                if not firebase_client.is_initialized():
                    self.ratings_container.content = ft.Text("Оценки недоступны офлайн", size=13, color=ft.colors.GREY)
                    self.page.update()
                    return
                data = firebase_client.get_book_ratings(self.book.id)
                self.ratings_data = data
                self.ratings_container.content = self._create_ratings_content()
                self.page.update()
            except Exception as e:
                logger.error(f"Ошибка загрузки оценок: {e}", exc_info=True)
                self.ratings_container.content = ft.Text("Не удалось загрузить оценки", size=13, color=ft.colors.GREY)
                self.page.update()
        import threading
        threading.Thread(target=_load, daemon=True).start()

    def _create_ratings_content(self) -> ft.Control:
        """Создает содержимое блока оценок и отзывов."""
        data = self.ratings_data
        avg = data.get("average", 0) or 0
        count = data.get("count", 0) or 0
        user_rating = data.get("userRating")
        reviews = data.get("reviews", []) or []

        stars = ft.Row([
            self._make_star(i)
            for i in range(1, 6)
        ], spacing=2)

        header = ft.Row([
            ft.Text("Оценки", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True),
            ft.Text(f"★ {avg:.1f}" if avg else "нет оценок", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.AMBER),
            ft.Text(f"({count})", size=14, color=ft.colors.GREY),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

        review_items = []
        for rv in reviews[:20]:
            review_items.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.icons.ACCOUNT_CIRCLE, size=20, color=ft.colors.PRIMARY),
                        ft.Text(rv.get("nickname", "Читатель"), weight=ft.FontWeight.BOLD, size=13),
                        ft.Container(expand=True),
                        ft.Text("★" * int(rv.get("rating", 0)), size=13, color=ft.colors.AMBER),
                    ], spacing=6),
                    ft.Text(rv.get("review", ""), size=13),
                ], spacing=4),
                padding=10,
                bgcolor=ft.colors.SURFACE_VARIANT,
                border_radius=8,
                margin=ft.margin.only(bottom=6),
            ))

        review_list = ft.Column(review_items, spacing=0) if review_items else ft.Text(
            "Отзывов пока нет. Станьте первым!", size=13, color=ft.colors.GREY
        )

        return ft.Container(
            content=ft.Column([
                ft.Divider(),
                header,
                ft.Row([
                    stars,
                    ft.Container(expand=True),
                    ft.TextButton(
                        "Написать отзыв" if user_rating is None else "Изменить оценку",
                        icon=ft.icons.EDIT,
                        on_click=self._show_rate_dialog,
                    ),
                    ft.TextButton(
                        "Удалить оценку",
                        icon=ft.icons.DELETE,
                        on_click=self._on_delete_rating,
                        visible=user_rating is not None,
                    ),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(),
                ft.Text("Отзывы читателей", size=15, weight=ft.FontWeight.BOLD),
                review_list,
            ], spacing=10),
            padding=ft.padding.only(top=10),
        )

    def _make_star(self, value: int) -> ft.IconButton:
        """Создает звезду для отображения средней оценки (неинтерактивная)."""
        data = self.ratings_data
        avg = data.get("average", 0) or 0
        filled = value <= round(avg)
        return ft.IconButton(
            icon=ft.icons.STAR if filled else ft.icons.STAR_BORDER,
            icon_color=ft.colors.AMBER if filled else ft.colors.OUTLINE,
            icon_size=22,
            disabled=True,
        )

    def _show_rate_dialog(self, e=None):
        """Диалог оценки и отзыва."""
        self._rate_value = self.ratings_data.get("userRating") or 0
        self._rate_stars = ft.Row([
            self._make_rate_star(i) for i in range(1, 6)
        ], spacing=4)
        self._rate_review_field = ft.TextField(
            label="Ваш отзыв (необязательно)",
            multiline=True,
            min_lines=2,
            max_lines=5,
            value="",
        )
        dlg = ft.AlertDialog(
            title=ft.Text(f"Оценить книгу: {self.book.title[:40]}"),
            content=ft.Column([
                self._rate_stars,
                self._rate_review_field,
            ], tight=True, spacing=12, width=360),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.close(dlg)),
                ft.ElevatedButton("Сохранить", icon=ft.icons.SAVE, on_click=lambda _: self._submit_rating(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._rate_dlg = dlg
        self.page.open(dlg)
        self.page.update()

    def _make_rate_star(self, value: int) -> ft.IconButton:
        filled = value <= self._rate_value
        return ft.IconButton(
            icon=ft.icons.STAR if filled else ft.icons.STAR_BORDER,
            icon_color=ft.colors.AMBER if filled else ft.colors.OUTLINE,
            icon_size=30,
            on_click=lambda e, v=value: self._set_rate_value(v),
        )

    def _set_rate_value(self, value: int):
        self._rate_value = value
        for i, star in enumerate(self._rate_stars.controls, start=1):
            star.icon = ft.icons.STAR if i <= value else ft.icons.STAR_BORDER
            star.icon_color = ft.colors.AMBER if i <= value else ft.colors.OUTLINE
        self.page.update()

    def _submit_rating(self, dlg):
        if self._rate_value < 1:
            return
        review = (self._rate_review_field.value or "").strip()

        def _do():
            try:
                from src.core.firebase_client import auth_session, firebase_client
                nickname = auth_session.nickname or ""
                data = firebase_client.rate_book(self.book.id, self._rate_value, review, nickname)
                if data:
                    self.ratings_data = data
                self.page.close(dlg)
                self.ratings_container.content = self._create_ratings_content()
                self.page.update()
            except Exception as ex:
                logger.error(f"Ошибка сохранения оценки: {ex}", exc_info=True)
        import threading
        threading.Thread(target=_do, daemon=True).start()

    def _on_delete_rating(self, e=None):
        def _do():
            try:
                from src.core.firebase_client import firebase_client
                firebase_client.delete_rating(self.book.id)
                data = firebase_client.get_book_ratings(self.book.id)
                self.ratings_data = data
                self.ratings_container.content = self._create_ratings_content()
                self.page.update()
            except Exception as ex:
                logger.error(f"Ошибка удаления оценки: {ex}", exc_info=True)
        import threading
        threading.Thread(target=_do, daemon=True).start()

    def build(self) -> ft.Control:
        """Возвращает содержимое страницы"""
        return self.content
