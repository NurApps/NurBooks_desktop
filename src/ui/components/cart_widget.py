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

        # Создаем UI элементы
        self.cart_list = ft.ListView(expand=True, spacing=5)
        self.total_label = ft.Text("Книг в корзине: 0", size=14)
        self.download_button = ft.ElevatedButton(
            "Скачать все",
            icon=ft.icons.DOWNLOAD,
            on_click=self._on_download_all_click,
            disabled=True
        )
        self.clear_button = ft.TextButton(
            "Очистить корзину",
            icon=ft.icons.DELETE,
            on_click=self._on_clear_cart
        )

        self.content = self._create_content()

    def add_book(self, book: Book):
        """Добавляет книгу в корзину"""
        # Проверяем, нет ли уже этой книги в корзине
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
        """Удаляет книгу из корзины"""
        self.items = [item for item in self.items if item['book'].id != book_id]
        self._update_cart()

    def get_selected_books(self) -> list[Book]:
        """Возвращает выбранные книги"""
        return [item['book'] for item in self.items if item['selected']]

    def get_all_books(self) -> list[Book]:
        """Возвращает все книги в корзине"""
        return [item['book'] for item in self.items]

    def _create_cart_item(self, item: dict[str, Any]) -> ft.Control:
        """Создает элемент корзины"""
        book = item['book']

        return ft.Container(
            content=ft.Row([
                # Чекбокс выбора
                ft.Checkbox(
                    value=item['selected'],
                    on_change=lambda e, bid=book.id: self._on_item_select(bid, e.control.value)
                ),

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
                    tooltip="Удалить",
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
        """Создает содержимое виджета корзины"""
        return ft.Container(
            content=ft.Column([
                # Заголовок
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.icons.CLOSE,
                            icon_size=20,
                            tooltip="Скрыть корзину",
                            on_click=lambda e: self.on_close() if self.on_close else None
                        ),
                        ft.Icon(ft.icons.SHOPPING_CART, size=20, color=ft.colors.PRIMARY),
                        ft.Text("Корзина для скачивания", size=16, weight=ft.FontWeight.BOLD),
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

                # Список книг или пустая корзина
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

    def _update_cart(self):
        """Обновляет содержимое корзины"""
        # Обновляем список
        self.cart_list.controls.clear()
        for item in self.items:
            self.cart_list.controls.append(self._create_cart_item(item))

        # Обновляем счетчик
        selected_count = len([item for item in self.items if item['selected']])
        total_count = len(self.items)
        self.total_label.value = f"Выбрано: {selected_count} из {total_count}"

        # Обновляем состояние кнопки
        self.download_button.disabled = selected_count == 0

        # Если корзина пуста, показываем сообщение
        if total_count == 0:
            self.cart_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.SHOPPING_CART_OUTLINED, size=48, color=ft.colors.GREY),
                        ft.Text("Корзина пуста", size=16, color=ft.colors.GREY),
                        ft.Text("Добавьте книги из каталога", size=12, color=ft.colors.GREY_600),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )

    def _on_item_select(self, book_id: int, selected: bool):
        """Обработчик выбора/снятия выбора книги"""
        for item in self.items:
            if item['book'].id == book_id:
                item['selected'] = selected
                break
        self._update_cart()

    def _on_remove_item(self, book_id: int):
        """Обработчик удаления книги из корзины"""
        self.remove_book(book_id)
        if self.on_remove_item:
            self.on_remove_item(book_id)

    def _on_download_all_click(self, e):
        """Обработчик скачивания всех выбранных книг"""
        selected_books = self.get_selected_books()
        if selected_books and self.on_download_all:
            self.on_download_all(selected_books)

    def _on_clear_cart(self, e):
        """Обработчик очистки корзины"""
        self.items.clear()
        self._update_cart()

    def build(self) -> ft.Control:
        """Возвращает виджет корзины"""
        return self.content

    def show(self):
        """Показывает корзину"""
        self._update_cart()
        return self.content
