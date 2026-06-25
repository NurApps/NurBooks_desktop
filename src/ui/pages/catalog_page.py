import flet as ft
from typing import List
from src.core.storage import Storage
from src.core.models import Book
from src.ui.components.search_bar import SearchBar
from src.ui.components.filters_panel import FiltersPanel


class CatalogPage:
    def __init__(self, page: ft.Page, on_book_click=None):
        self.page = page
        self.on_book_click = on_book_click
        self.storage = Storage()
        self.books: List[Book] = self.storage.load_books()
        self.filtered_books: List[Book] = self.books.copy()

        self.search_bar = SearchBar(on_search=None)
        self.filters_panel = FiltersPanel(on_filter_change=self._on_filter_change)
        self.search_bar.search_field.on_submit = self._apply_filters_and_search

        self._setup_filters()
        self.book_grid = self._create_book_grid()
        self.content = self._create_content()

    def _setup_filters(self):
        if not self.books:
            return
        all_categories = sorted(list(set(book.category for book in self.books if book.category)))
        all_authors = sorted(list(set(book.author for book in self.books if book.author)))
        all_years = sorted(list(set(str(book.year) for book in self.books if book.year)), reverse=True)
        self.filters_panel.set_categories(all_categories)
        self.filters_panel.set_authors(all_authors)
        self.filters_panel.set_years(all_years)

    def _create_book_card(self, book: Book) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Image(
                            src=book.cover if book.cover else "assets/logo.png",
                            width=150,
                            height=200,
                            fit=ft.ImageFit.COVER,
                            border_radius=ft.border_radius.all(5),
                        ),
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(
                        book.title,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        book.author,
                        size=11,
                        color=ft.colors.GREY_700,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        f"{book.year} • {book.category}",
                        size=10,
                        color=ft.colors.GREY_600,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        f"👁 {getattr(book, 'view_count', 0)}  ⬇ {getattr(book, 'download_count', 0)}",
                        size=9,
                        color=ft.colors.GREY_600,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=180,
            height=310,
            padding=10,
            bgcolor=ft.colors.SURFACE_VARIANT,
            border_radius=10,
            on_click=lambda e, b=book: self._on_book_click(b),
            tooltip=book.title,
            ink=True,
        )

    def _create_book_grid(self) -> ft.Control:
        if not self.filtered_books:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.icons.BOOK, size=48, color=ft.colors.GREY),
                        ft.Text("Книги не найдены", size=16, color=ft.colors.GREY),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=20,
                alignment=ft.alignment.center,
            )

        return ft.GridView(
            controls=[self._create_book_card(book) for book in self.filtered_books],
            max_extent=200,
            child_aspect_ratio=0.77,
            spacing=15,
            run_spacing=15,
            padding=20,
            expand=True,
        )

    def _create_content(self) -> ft.Control:
        search_layout = ft.Row(
            controls=[
                self.search_bar.search_field,
                ft.IconButton(icon=ft.icons.SEARCH, tooltip="Найти", on_click=self._apply_filters_and_search),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        filters_layout = ft.Column(
            controls=[
                self.filters_panel.build(),
            ]
        )

        self.grid_container = ft.Container(content=self.book_grid, expand=True, margin=ft.margin.only(right=20))
        self.stats_text = ft.Text(
            f"Найдено книг: {len(self.filtered_books)} из {len(self.books)}",
            size=12,
            color=ft.colors.GREY,
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column(
                            [ft.Text("Каталог книг", size=28, weight=ft.FontWeight.BOLD), search_layout],
                            spacing=10,
                        ),
                        padding=ft.padding.only(left=20, right=20, top=20, bottom=10),
                    ),
                    ft.Row(
                        [
                            ft.Container(content=filters_layout, width=250, margin=ft.margin.only(left=20)),
                            self.grid_container,
                        ],
                        expand=True,
                    ),
                    ft.Container(content=self.stats_text, padding=ft.padding.only(left=20, right=20, bottom=10)),
                ]
            ),
            expand=True,
        )

    def _apply_filters_and_search(self, e=None):
        query = self.search_bar.search_field.value.lower().strip() if self.search_bar.search_field.value else ""
        category = self.filters_panel.category_dropdown.value
        author = self.filters_panel.author_dropdown.value
        year = self.filters_panel.year_dropdown.value
        sort_mode = self.filters_panel.sort_dropdown.value

        results = self.books
        if query:
            results = [book for book in results if query in book.title.lower() or query in book.author.lower()]
        if category and category != "Все категории":
            results = [book for book in results if book.category == category]
        if author and author != "Все авторы":
            results = [book for book in results if book.author == author]
        if year and year != "Все годы":
            results = [book for book in results if str(book.year) == year]

        if sort_mode == "По популярности":
            results = sorted(
                results,
                key=lambda b: getattr(b, "view_count", 0) + getattr(b, "download_count", 0) * 3,
                reverse=True,
            )
        elif sort_mode == "По просмотрам":
            results = sorted(results, key=lambda b: getattr(b, "view_count", 0), reverse=True)
        elif sort_mode == "По скачиваниям":
            results = sorted(results, key=lambda b: getattr(b, "download_count", 0), reverse=True)

        self.filtered_books = results
        self._update_book_grid()

    def _on_filter_change(self, filters):
        self._apply_filters_and_search()

    def _update_book_grid(self):
        self.book_grid = self._create_book_grid()
        self.grid_container.content = self.book_grid
        self.stats_text.value = f"Найдено книг: {len(self.filtered_books)} из {len(self.books)}"
        if self.page:
            self.page.update()

    def _on_book_click(self, book: Book):
        if self.on_book_click:
            self.on_book_click(book)

    def build(self) -> ft.Control:
        return self.content
