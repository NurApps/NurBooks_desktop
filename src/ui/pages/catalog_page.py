import threading

import flet as ft

from src.core.models import Book
from src.ui.components.filters_panel import FiltersPanel
from src.ui.components.search_bar import SearchBar


class CatalogPage:
    def __init__(self, page: ft.Page, books: list[Book], on_book_click=None, on_continue_reading=None, reading_progress: dict | None = None, on_refresh=None):
        self.page = page
        self.on_book_click = on_book_click
        self.on_continue_reading = on_continue_reading
        self.on_refresh = on_refresh
        self.books: list[Book] = books
        self.filtered_books: list[Book] = books.copy()
        self._search_timer = None
        self._reading_progress = reading_progress

        self.filters_panel = FiltersPanel(on_filter_change=self._on_filter_change)
        self.search_bar = SearchBar(on_search=None)
        self.search_bar.search_field.on_change = self._on_search_change
        self.search_bar.search_field.hint_text = "Поиск по названию или автору..."
        self.search_bar.filter_button.on_click = self._toggle_filters
        self._filters_visible = not self._is_mobile()

        self._setup_filters()
        self.book_grid = None
        self.content = self._create_content()
        self._rebuild_grid()

    def _is_mobile(self) -> bool:
        """Определяет, мобильный ли экран"""
        width = self.page.width
        if width is None:
            window = getattr(self.page, "window", None)
            width = window.width if window is not None else 1200
        return width < 700

    def _toggle_filters(self, e=None):
        """Показывает/скрывает панель фильтров (для мобильных)"""
        self._filters_visible = not self._filters_visible
        if hasattr(self, 'filters_container'):
            self.filters_container.visible = self._filters_visible
            self.filters_divider.visible = self._filters_visible
        self.page.update()

    def _on_refresh_click(self, e=None):
        """Перезагружает каталог с сервера."""
        self.refresh_button.icon = ft.icons.REFRESH
        self.refresh_button.rotate = ft.Rotate(0, alignment=ft.alignment.center)
        self.refresh_button.icon_color = ft.colors.PRIMARY
        self.page.update()

        if self.on_refresh:
            self.on_refresh()
        else:
            try:
                from src.core.storage import Storage
                books = Storage().load_books(force=True)
                if books:
                    self.books = books
                    self.filtered_books = books.copy()
                    self._setup_filters()
                    self._rebuild_grid()
                    self.page.update()
            except Exception:
                pass

    def _setup_filters(self):
        if not self.books:
            return
        cats = set()
        auths = set()
        yrs = set()
        for b in self.books:
            if b.category:
                cats.add(b.category)
            if b.author:
                auths.add(b.author)
            if b.year:
                yrs.add(str(b.year))
        self.filters_panel.set_categories(sorted(cats))
        self.filters_panel.set_authors(sorted(auths))
        self.filters_panel.set_years(sorted(yrs, reverse=True))

    def _create_book_card(self, book: Book) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Stack([
                            ft.Container(
                                bgcolor=ft.colors.GREY_300,
                                width=150, height=200,
                                border_radius=5,
                            ),
                            ft.Image(
                                src=book.cover if book.cover else "assets/logo.png",
                                width=150, height=200,
                                fit=ft.ImageFit.COVER,
                                border_radius=ft.border_radius.all(5),
                            ),
                        ]),
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(book.title, size=14, weight=ft.FontWeight.BOLD,
                            color=ft.colors.ON_SURFACE,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER),
                    ft.Text(book.author, size=11, color=ft.colors.ON_SURFACE_VARIANT,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER),
                    ft.Text(f"{book.year} • {book.category}", size=10, color=ft.colors.ON_SURFACE_VARIANT,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER),
                    ft.Text(f"👁 {getattr(book, 'view_count', 0)}  ⬇ {getattr(book, 'download_count', 0)}",
                            size=9, color=ft.colors.OUTLINE, text_align=ft.TextAlign.CENTER),
                ],
                spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=180, height=310, padding=10,
            bgcolor=ft.colors.SURFACE_VARIANT, border_radius=10,
            on_click=lambda e, b=book: self._on_book_click(b),
            ink=True,
        )

    def _build_empty_state(self) -> ft.Container:
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.BOOK, size=48, color=ft.colors.GREY),
                ft.Text("Книги не найдены", size=16, color=ft.colors.GREY),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20, alignment=ft.alignment.center,
        )

    def _load_reading_progress(self) -> dict[int, int]:
        if self._reading_progress is not None:
            return self._reading_progress
        try:
            from src.core.database import Database
            raw = Database().get_all_reading_progress()
            result = {}
            for key, page in (raw or {}).items():
                try:
                    result[int(key)] = int(page)
                except (TypeError, ValueError):
                    continue
            return result
        except Exception:
            return {}

    def _create_continue_reading_section(self) -> ft.Control:
        """Секция «Продолжить чтение» с книгами, которые пользователь начал читать."""
        progress = self._load_reading_progress()
        if not progress:
            return ft.Container(height=0)

        book_by_id = {b.id: b for b in self.books}
        items = []
        for book_id, page in list(progress.items())[:6]:
            book = book_by_id.get(book_id)
            if not book:
                continue
            items.append(ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Image(
                            src=book.cover if book.cover else "assets/logo.png",
                            width=140, height=185,
                            fit=ft.ImageFit.COVER,
                            border_radius=ft.border_radius.all(8),
                        ),
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(book.title, size=13, weight=ft.FontWeight.BOLD,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER),
                    ft.Text(f"Страница {page}", size=11, color=ft.colors.PRIMARY,
                            text_align=ft.TextAlign.CENTER),
                ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=170, padding=10,
                bgcolor=ft.colors.SURFACE_VARIANT, border_radius=10,
                on_click=lambda e, b=book, p=page: self._on_continue_reading(b, p),
                ink=True,
            ))

        if not items:
            return ft.Container(height=0)

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.HISTORY, size=20, color=ft.colors.PRIMARY),
                    ft.Text("Продолжить чтение", size=18, weight=ft.FontWeight.BOLD),
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=8, color=ft.colors.OUTLINE_VARIANT),
                ft.Row(
                    items,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=15,
                    run_spacing=15,
                ),
            ]),
            padding=ft.padding.only(left=20, right=20, top=10, bottom=5),
        )

    def _on_continue_reading(self, book: Book, page: int):
        if self.on_continue_reading:
            self.on_continue_reading(book, page)
        else:
            self._on_book_click(book)

    def _rebuild_grid(self):
        if not self.filtered_books:
            self.grid_container.content = self._build_empty_state()
        else:
            self.grid_container.content = ft.GridView(
                controls=[self._create_book_card(b) for b in self.filtered_books],
                max_extent=200, child_aspect_ratio=0.77,
                spacing=15, run_spacing=15, padding=20, expand=True,
            )
        self.stats_text.value = f"Найдено книг: {len(self.filtered_books)} из {len(self.books)}"

    def _create_content(self) -> ft.Control:
        self.stats_text = ft.Text(
            f"Найдено книг: {len(self.filtered_books)} из {len(self.books)}",
            size=12, color=ft.colors.GREY,
        )

        self.grid_container = ft.Container(expand=True)

        self.refresh_button = ft.IconButton(
            icon=ft.icons.REFRESH,
            tooltip="Обновить каталог",
            on_click=self._on_refresh_click,
            icon_color=ft.colors.PRIMARY
        )

        self.filters_container = ft.Container(
            self.filters_panel.build(),
            width=None if self._is_mobile() else 260,
            visible=self._filters_visible
        )
        self.filters_divider = ft.VerticalDivider(width=1)
        self.filters_divider.visible = self._filters_visible

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Каталог книг", size=28, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            self.stats_text,
                            self.refresh_button,
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        self.search_bar.search_field,
                    ], spacing=10),
                    padding=ft.padding.only(left=20, right=20, top=20, bottom=10),
                ),
                self._create_continue_reading_section(),
                ft.Row([
                    self.filters_container,
                    self.filters_divider,
                    self.grid_container,
                ], expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.START),
            ]),
            expand=True,
        )

    def _on_search_change(self, e):
        """Debounce поиска — ждём 300мс после последнего ввода"""
        if self._search_timer:
            self._search_timer.cancel()
        self._search_timer = threading.Timer(0.3, self._apply_filters_and_search)
        self._search_timer.start()

    def _apply_filters_and_search(self, e=None):
        sf = self.search_bar.search_field
        query = sf.value.lower().strip() if sf.value else ""
        category = self.filters_panel.category_dropdown.value
        author = self.filters_panel.author_dropdown.value
        year = self.filters_panel.year_dropdown.value
        sort_mode = self.filters_panel.sort_dropdown.value

        results = self.books
        if query:
            results = [b for b in results if query in b.title.lower() or query in b.author.lower()]
        if category and category != "Все категории":
            results = [b for b in results if b.category == category]
        if author and author != "Все авторы":
            results = [b for b in results if b.author == author]
        if year and year != "Все годы":
            results = [b for b in results if str(b.year) == year]

        if sort_mode == "По популярности":
            results = sorted(results, key=lambda b: b.view_count + b.download_count * 3, reverse=True)
        elif sort_mode == "По просмотрам":
            results = sorted(results, key=lambda b: b.view_count, reverse=True)
        elif sort_mode == "По скачиваниям":
            results = sorted(results, key=lambda b: b.download_count, reverse=True)

        self.filtered_books = results
        self._rebuild_grid()
        if self.page:
            self.page.update()

    def _on_filter_change(self, filters):
        self._apply_filters_and_search()

    def _on_book_click(self, book: Book):
        if self.on_book_click:
            self.on_book_click(book)

    def build(self) -> ft.Control:
        return self.content
