import flet as ft
from typing import List, Callable


class FiltersPanel:
    def __init__(self, on_filter_change: Callable = None):
        self.on_filter_change = on_filter_change
        self.categories = ["Все категории"]
        self.authors = ["Все авторы"]
        self.years = ["Все годы"]
        self.sort_options = ["По умолчанию", "По популярности", "По просмотрам", "По скачиваниям"]

        self.category_dropdown = ft.Dropdown(
            label="Категория",
            options=[ft.dropdown.Option("Все категории")],
            on_change=self._on_filter_change,
        )

        self.author_dropdown = ft.Dropdown(
            label="Автор",
            options=[ft.dropdown.Option("Все авторы")],
            on_change=self._on_filter_change,
        )

        self.year_dropdown = ft.Dropdown(
            label="Год",
            options=[ft.dropdown.Option("Все годы")],
            on_change=self._on_filter_change,
        )

        self.sort_dropdown = ft.Dropdown(
            label="Сортировка",
            value="По умолчанию",
            options=[ft.dropdown.Option(opt) for opt in self.sort_options],
            on_change=self._on_filter_change,
        )

    def set_categories(self, categories: List[str]):
        self.categories = ["Все категории"] + categories
        self.category_dropdown.options = [ft.dropdown.Option(cat) for cat in self.categories]

    def set_authors(self, authors: List[str]):
        self.authors = ["Все авторы"] + authors
        self.author_dropdown.options = [ft.dropdown.Option(author) for author in self.authors]

    def set_years(self, years: List[str]):
        self.years = ["Все годы"] + years
        self.year_dropdown.options = [ft.dropdown.Option(year) for year in self.years]

    def _on_filter_change(self, e):
        if self.on_filter_change:
            filters = {
                "category": self.category_dropdown.value,
                "author": self.author_dropdown.value,
                "year": self.year_dropdown.value,
                "sort": self.sort_dropdown.value,
            }
            self.on_filter_change(filters)

    def build(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Фильтры", size=16, weight=ft.FontWeight.BOLD),
                    self.category_dropdown,
                    self.author_dropdown,
                    self.year_dropdown,
                    self.sort_dropdown,
                ]
            ),
            padding=10,
            bgcolor=ft.colors.SURFACE_VARIANT,
            border_radius=10,
        )
