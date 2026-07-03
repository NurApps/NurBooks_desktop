import flet as ft
import threading
from typing import List
from src.core.models import Book
from src.ui.components.search_bar import SearchBar
from src.ui.components.filters_panel import FiltersPanel


class CatalogPage:
    def __init__(self, page: ft.Page, books: List[Book], on_book_click=None):
        self.page = page
        self.on_book_click = on_book_click
        self.books: List[Book] = books
        self.filtered_books: List[Book] = books.copy()
        self._search_timer = None

        self.search_bar = SearchBar(on_search=None)
        self.filters_panel = FiltersPanel(on_filter_change=self._on_filter_change)
        self.search_bar.search_field.on_change = self._on_search_change

        self._setup_filters()
        self.book_grid = None
        self.content = self._create_content()
        self._rebuild_grid()

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
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER),
                    ft.Text(book.author, size=11, color=ft.colors.GREY_700,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER),
                    ft.Text(f"{book.year} • {book.category}", size=10, color=ft.colors.GREY_600,
                            max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER),
                    ft.Text(f"👁 {getattr(book, 'view_count', 0)}  ⬇ {getattr(book, 'download_count', 0)}",
                            size=9, color=ft.colors.GREY_600, text_align=ft.TextAlign.CENTER),
                ],
                spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=180, height=310, padding=10,
            bgcolor=ft.colors.SURFACE_VARIANT, border_radius=10,
            on_click=lambda e, b=book: self._on_book_click(b),
            tooltip=book.title, ink=True,
        )

    def _build_empty_state(self) -> ft.Container:
        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.BOOK, size=48, color=ft.colors.GREY),
                ft.Text("Книги не найдены", size=16, color=ft.colors.GREY),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20, alignment=ft.alignment.center,
        )

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
        search_layout = ft.Row(
            controls=[
                self.search_bar.search_field,
                ft.IconButton(icon=ft.icons.SEARCH, tooltip="Найти", on_click=self._apply_filters_and_search),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.grid_container = ft.Container(expand=True, margin=ft.margin.only(right=20))
        self.stats_text = ft.Text(
            f"Найдено книг: {len(self.filtered_books)} из {len(self.books)}",
            size=12, color=ft.colors.GREY,
        )

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Column(
                        [ft.Text("Каталог книг", size=28, weight=ft.FontWeight.BOLD), search_layout],
                        spacing=10,
                    ),
                    padding=ft.padding.only(left=20, right=20, top=20, bottom=10),
                ),
                ft.Row([
                    ft.Container(content=self.filters_panel.build(), width=250, margin=ft.margin.only(left=20)),
                    self.grid_container,
                ], expand=True),
                ft.Container(content=self.stats_text, padding=ft.padding.only(left=20, right=20, bottom=10)),
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
