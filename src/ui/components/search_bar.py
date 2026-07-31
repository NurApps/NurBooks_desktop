import flet as ft


class SearchBar:
    def __init__(self, on_search=None, on_filter_click=None):
        self.on_search = on_search
        self.on_filter_click = on_filter_click
        self.search_field = ft.TextField(
            label="Поиск книг...",
            prefix_icon=ft.icons.SEARCH,
            expand=True,
            on_change=self._on_search_change
        )
        self.filter_button = ft.IconButton(
            icon=ft.icons.FILTER_LIST,
            on_click=self._on_filter_click
        )

    def _on_search_change(self, e):
        if self.on_search:
            self.on_search(self.search_field.value)

    def _on_filter_click(self, e):
        if self.on_filter_click:
            self.on_filter_click()

    def build(self) -> ft.Control:
        return ft.Row([
            self.search_field,
            self.filter_button
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
