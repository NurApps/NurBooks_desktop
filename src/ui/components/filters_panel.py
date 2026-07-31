from collections.abc import Callable

import flet as ft


class FiltersPanel:
    def __init__(self, on_filter_change: Callable = None):
        self.on_filter_change = on_filter_change
        self.categories = ["Все категории"]
        self.authors = ["Все авторы"]
        self.years = ["Все годы"]
        self.sort_options = ["По умолчанию", "По популярности", "По просмотрам", "По скачиваниям"]

        self.category_dropdown = ft.Dropdown(
            label="Категория",
            hint_text="Выберите категорию",
            options=[ft.dropdown.Option("Все категории")],
            on_change=self._on_filter_change,
            text_size=13,
        )

        self.author_dropdown = ft.Dropdown(
            label="Автор",
            hint_text="Выберите автора",
            options=[ft.dropdown.Option("Все авторы")],
            on_change=self._on_filter_change,
            text_size=13,
        )

        self.year_dropdown = ft.Dropdown(
            label="Год",
            hint_text="Выберите год",
            options=[ft.dropdown.Option("Все годы")],
            on_change=self._on_filter_change,
            text_size=13,
        )

        self.sort_dropdown = ft.Dropdown(
            label="Сортировка",
            value="По умолчанию",
            options=[ft.dropdown.Option(opt) for opt in self.sort_options],
            on_change=self._on_filter_change,
            text_size=13,
        )

        self.clear_button = ft.TextButton(
            "Сбросить фильтры",
            icon=ft.icons.CLEAR,
            on_click=self._on_clear,
            visible=False,
        )

    def set_categories(self, categories: list[str]):
        self.categories = ["Все категории"] + categories
        self.category_dropdown.options = [ft.dropdown.Option(cat) for cat in self.categories]

    def set_authors(self, authors: list[str]):
        self.authors = ["Все авторы"] + authors
        self.author_dropdown.options = [ft.dropdown.Option(author) for author in self.authors]

    def set_years(self, years: list[str]):
        self.years = ["Все годы"] + years
        self.year_dropdown.options = [ft.dropdown.Option(year) for year in self.years]

    def _on_filter_change(self, e):
        has_active = any([
            self.category_dropdown.value and self.category_dropdown.value != "Все категории",
            self.author_dropdown.value and self.author_dropdown.value != "Все авторы",
            self.year_dropdown.value and self.year_dropdown.value != "Все годы",
        ])
        self.clear_button.visible = has_active
        if self.on_filter_change:
            filters = {
                "category": self.category_dropdown.value,
                "author": self.author_dropdown.value,
                "year": self.year_dropdown.value,
                "sort": self.sort_dropdown.value,
            }
            self.on_filter_change(filters)

    def _on_clear(self, e):
        self.category_dropdown.value = "Все категории"
        self.author_dropdown.value = "Все авторы"
        self.year_dropdown.value = "Все годы"
        self.sort_dropdown.value = "По умолчанию"
        self.clear_button.visible = False
        self._on_filter_change(e)

    def build(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row([
                        ft.Icon(ft.icons.FILTER_LIST, size=18, color=ft.colors.PRIMARY),
                        ft.Text("Фильтры", size=16, weight=ft.FontWeight.BOLD),
                    ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Divider(height=1, color=ft.colors.OUTLINE_VARIANT),
                    ft.Container(height=8),
                    self.category_dropdown,
                    ft.Container(height=8),
                    self.author_dropdown,
                    ft.Container(height=8),
                    self.year_dropdown,
                    ft.Divider(height=1, color=ft.colors.OUTLINE_VARIANT),
                    ft.Container(height=8),
                    self.sort_dropdown,
                    ft.Container(height=8),
                    self.clear_button,
                ],
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.padding.all(16),
            bgcolor=ft.colors.SURFACE_VARIANT,
            border_radius=12,
            border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
        )
