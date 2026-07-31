
import flet as ft

from src.core.models import Author


class AuthorsPage:
    def __init__(self, page: ft.Page, authors: list[Author], on_author_click=None):
        self.page = page
        self.on_author_click = on_author_click
        self.authors: list[Author] = authors
        self.content = self._create_content()

    def _create_author_card(self, author: Author) -> ft.Control:
        bio_text = author.bio[:150] + "..." if len(author.bio) > 150 else author.bio
        bio_text = bio_text if bio_text != "null" else ""

        return ft.Container(
            content=ft.Column([
                ft.Text(author.name, size=18, weight=ft.FontWeight.BOLD,
                        max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),

                ft.Container(
                    content=ft.Text(bio_text, size=12, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS),
                    padding=5, bgcolor=ft.colors.SURFACE_VARIANT, border_radius=5,
                ) if bio_text else ft.Container(height=0),

                ft.Text(f"Книг: {len(author.books)}", size=12, color=ft.colors.GREY),

                ft.Container(
                    content=ft.TextButton("Просмотреть книги",
                        on_click=lambda e, a=author: self._on_author_click(a)),
                    alignment=ft.alignment.center_right
                ),
            ], spacing=8),
            padding=15,
            bgcolor=ft.colors.SURFACE_VARIANT,
            border_radius=10, ink=True,
            on_click=lambda e, a=author: self._on_author_click(a),
            width=300, height=200
        )

    def _create_content(self) -> ft.Control:
        if not self.authors:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.PERSON, size=48, color=ft.colors.GREY),
                    ft.Text("Авторы не найдены", size=16, color=ft.colors.GREY)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20, alignment=ft.alignment.center
            )

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text("Авторы", size=28, weight=ft.FontWeight.BOLD),
                    padding=ft.padding.only(left=20, right=20, top=20, bottom=10)
                ),
                ft.Container(
                    content=ft.GridView(
                        controls=[self._create_author_card(a) for a in self.authors],
                        max_extent=320, child_aspect_ratio=1.5,
                        spacing=15, run_spacing=15, padding=20, expand=True
                    ),
                    expand=True
                ),
                ft.Container(
                    content=ft.Text(f"Всего авторов: {len(self.authors)}", size=12, color=ft.colors.GREY),
                    padding=ft.padding.only(left=20, right=20, bottom=10)
                ),
            ]),
            expand=True
        )

    def _on_author_click(self, author: Author):
        """Обработчик клика по автору"""
        if self.on_author_click:
            self.on_author_click(author)

    def build(self) -> ft.Control:
        """Возвращает содержимое страницы"""
        return self.content
