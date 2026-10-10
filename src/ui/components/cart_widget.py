from collections.abc import Callable
from typing import Any

import flet as ft

from src.core.models import Book


class CartWidget:
    def __init__(self, on_download_all: Callable = None, on_remove_item: Callable = None, on_close: Callable = None):
        self.on_download_all = on_download_all
        self.on_remove_item = on_remove_item
        self.on_close = on_close
        self.items: list[dict[str, Any]] = []  # [{book: Book, selected: bool}]

        # Создаем UI элементы (очередь загрузки: без выбора, качаем всё разом)
        self.cart_list = ft.ListView(expand=True, spacing=5)
        self.total_label = ft.Text("Книг в очереди: 0", size=14)
        self._downloading = False
        self.download_button = ft.ElevatedButton(
            "Скачать",
            icon=ft.icons.DOWNLOAD,
            on_click=self._on_download_all_click,
            disabled=True
        )
        self.clear_button = ft.TextButton(
            "Очистить очередь",
            icon=ft.icons.DELETE,
            on_click=self._on_clear_cart
        )

        self.content = self._create_content()

    def add_book(self, book: Book):
        """Добавляет книгу в очередь загрузки"""
        # Проверяем, нет ли уже этой книги в очереди загрузки
        for item in self.items:
            if item['book'].id == book.id:
                return False

        self.items.append({
            'book': book,
            'selected': True
        })
        self._update_cart()
        return True

    def remove_book(self, book_id: int):
        """Удаляет книгу из очереди загрузки"""
        self.items = [item for item in self.items if item['book'].id != book_id]
        self._update_cart()

    def get_selected_books(self) -> list[Book]:
        """Возвращает выбранные книги"""
        return [item['book'] for item in self.items if item['selected']]

    def get_all_books(self) -> list[Book]:
        """Возвращает все книги в очереди загрузки"""
        return [item['book'] for item in self.items]

    def _create_cart_item(self, item: dict[str, Any]) -> ft.Control:
        """Создает элемент очереди загрузки"""
        book = item['book']

        return ft.Container(
            content=ft.Row([
                # Иконка
                ft.Container(
                    content=ft.Icon(ft.icons.PICTURE_AS_PDF, color=ft.colors.RED, size=22),
                    bgcolor=ft.colors.RED_50,
                    border_radius=20,
                    width=40,
                    height=40,
                    alignment=ft.alignment.center,
                ),

                # Информация о книге
                ft.Column([
                    ft.Text(book.title, size=13, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Автор: {book.author}", size=11, color=ft.colors.ON_SURFACE_VARIANT),
                    ft.Text(f"Категория: {book.category}", size=10, color=ft.colors.OUTLINE),
                ], expand=True, spacing=1),

                # Кнопка удаления
                ft.IconButton(
                    icon=ft.icons.DELETE_OUTLINE,
                    icon_size=16,
                    tooltip="Убрать из очереди",
                    on_click=lambda e, bid=book.id: self._on_remove_item(bid)
                ),
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            bgcolor=ft.colors.SURFACE,
            border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
            border_radius=12,
            margin=ft.margin.only(bottom=8)
        )

    def _create_content(self) -> ft.Control:
        """Создает содержимое виджета очереди загрузки"""
        return ft.Container(
            content=ft.Column([
                # Заголовок
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.icons.CLOSE,
                            icon_size=20,
                            tooltip="Скрыть очередь",
                            on_click=lambda e: self.on_close() if self.on_close else None
                        ),
                        ft.Icon(ft.icons.DOWNLOAD, size=20, color=ft.colors.PRIMARY),
                        ft.Text("Очередь загрузки", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.TextButton(
                            "Очистить",
                            icon=ft.icons.DELETE,
                            on_click=self._on_clear_cart
                        ),
                    ]),
                    padding=ft.padding.symmetric(horizontal=5, vertical=10),
                    bgcolor=ft.colors.SURFACE_VARIANT,
                ),

                ft.Divider(height=1),

                # Список книг или пустая очередь
                ft.Container(
                    content=ft.Column([
                        self.total_label,
                        self.cart_list,
                    ], expand=True),
                    padding=10,
                    expand=True
                ),

                # Кнопка скачивания
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            self.download_button,
                        ], alignment=ft.MainAxisAlignment.CENTER),
                    ]),
                    padding=ft.padding.symmetric(horizontal=10, vertical=8)
                ),
            ]),
            width=350,
            height=500,
            bgcolor=ft.colors.BACKGROUND,
            border=ft.border.all(1, ft.colors.OUTLINE),
            border_radius=10,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.colors.BLACK12,
                offset=ft.Offset(0, 0),
            )
        )

    def set_downloading(self, busy: bool):
        """Состояние скачивания: честный статус вместо молчаливого thread."""
        self._downloading = busy
        self._update_cart()

    def _update_cart(self):
        """Обновляет содержимое очереди"""
        # Обновляем список
        self.cart_list.controls.clear()
        for item in self.items:
            self.cart_list.controls.append(self._create_cart_item(item))

        total_count = len(self.items)
        if total_count == 1:
            self.total_label.value = "В очереди: 1 книга"
        else:
            self.total_label.value = f"В очереди: {total_count} книг"

        # Обновляем состояние кнопки
        if self._downloading:
            self.download_button.text = "Скачивание…"
            self.download_button.disabled = True
        else:
            self.download_button.text = f"Скачать ({total_count})" if total_count else "Скачать"
            self.download_button.disabled = total_count == 0

        # Если очередь пуста, показываем сообщение
        if total_count == 0:
            self.cart_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.DOWNLOAD_OUTLINED, size=48, color=ft.colors.GREY),
                        ft.Text("Очередь пуста", size=16, color=ft.colors.GREY),
                        ft.Text("Добавьте книги из каталога", size=12, color=ft.colors.GREY_600),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )

    def _on_item_select(self, book_id: int, selected: bool):
        """Оставлен для совместимости: выбор больше не используется, всё качается."""
        self._update_cart()

    def _on_remove_item(self, book_id: int):
        """Обработчик удаления книги из очереди"""
        self.remove_book(book_id)
        if self.on_remove_item:
            self.on_remove_item(book_id)

    def _on_download_all_click(self, e):
        """Обработчик скачивания всех книг из очереди"""
        books = self.get_all_books()
        if books and self.on_download_all:
            self.on_download_all(books)

    def _on_clear_cart(self, e):
        """Обработчик очистки очереди"""
        self.items.clear()
        self._update_cart()

    def build(self) -> ft.Control:
        """Возвращает виджет очереди загрузки"""
        return self.content

    def show(self):
        """Показывает очередь загрузки"""
        self._update_cart()
        return self.content
