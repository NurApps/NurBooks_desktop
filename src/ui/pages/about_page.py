import webbrowser

import flet as ft

from src.config import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    CONTACT_EMAIL,
    DESIGNERS,
    DEVELOPERS,
    TELEGRAM_CONTACTS,
    TESTERS,
)


class AboutPage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.content = self._create_content()

    def _create_content(self) -> ft.Control:
        """Создает содержимое страницы о приложении"""
        return ft.Container(
            content=ft.Column([
                # Заголовок и логотип
                ft.Container(
                    content=ft.Column([
                        ft.Image(
                            src="assets/logo.jpg" if self.page.theme_mode == ft.ThemeMode.LIGHT else "assets/logo.jpg",
                            width=120,
                            height=120,
                            fit=ft.ImageFit.CONTAIN,
                            border_radius=60,
                        ),
                        ft.Text(
                            APP_NAME,
                            size=32,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Text(
                            APP_DESCRIPTION,
                            size=16,
                            color=ft.colors.GREY,
                            text_align=ft.TextAlign.CENTER
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.only(top=40, bottom=20),
                    alignment=ft.alignment.center
                ),

                # Информация о версии
                ft.Container(
                    content=ft.Column([
                        ft.Text("Информация", size=20, weight=ft.FontWeight.BOLD),
                        ft.Divider(),

                        ft.Row([
                            ft.Text("Версия:", width=150),
                            ft.Text(APP_VERSION, weight=ft.FontWeight.BOLD),
                        ]),

                        ft.Row([
                            ft.Text("Разработчики:", width=150),
                            ft.Text(", ".join(DEVELOPERS), weight=ft.FontWeight.BOLD),
                        ]),

                        ft.Row([
                            ft.Text("Тестировщики:", width=150),
                            ft.Text(", ".join(TESTERS), weight=ft.FontWeight.BOLD),
                        ]),

                        ft.Row([
                            ft.Text("Дизайнеры", width=150),
                            ft.Text(", ".join(DESIGNERS), weight=ft.FontWeight.BOLD),
                        ]),

                        ft.Row([
                            ft.Text("Дата сборки:", width=150),
                            ft.Text("2026", weight=ft.FontWeight.BOLD),
                        ]),

                    ], spacing=10),
                    padding=20,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                    border_radius=10,
                    margin=ft.margin.symmetric(horizontal=20, vertical=10)
                ),

                # Контакты
                ft.Container(
                    content=ft.Column([
                        ft.Text("Контакты и поддержка", size=20, weight=ft.FontWeight.BOLD),
                        ft.Divider(),

                        ft.Row([
                            ft.Icon(ft.icons.EMAIL, color=ft.colors.BLUE),
                            ft.Text("Основной email:", width=120),
                            ft.Text(CONTACT_EMAIL, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.IconButton(
                                icon=ft.icons.CONTENT_COPY,
                                icon_size=16,
                                tooltip="Копировать",
                                on_click=lambda e: self._copy_to_clipboard(CONTACT_EMAIL)
                            ),
                        ]),

                        ft.Row([
                            ft.Icon(ft.icons.TELEGRAM, color=ft.colors.BLUE),
                            ft.Text("Telegram:", width=120),
                            ft.Text(TELEGRAM_CONTACTS[0] if len(TELEGRAM_CONTACTS) > 0 else "Не указан", weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            ft.IconButton(
                                icon=ft.icons.CONTENT_COPY,
                                icon_size=16,
                                tooltip="Копировать",
                                on_click=lambda e: self._copy_to_clipboard(TELEGRAM_CONTACTS[0]) if len(TELEGRAM_CONTACTS) > 0 else None
                            ),
                        ]),

                    ], spacing=10),
                    padding=20,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                    border_radius=10,
                    margin=ft.margin.symmetric(horizontal=20, vertical=10)
                ),

                # Поддержка
                ft.Container(
                    content=ft.Column([
                        ft.Text("Поддержать проект", size=20, weight=ft.FontWeight.BOLD),
                        ft.Divider(),

                        ft.Text(
                            "Если вам нравится приложение, вы можете поддержать нас финансово!",
                            text_align=ft.TextAlign.CENTER
                        ),

                        ft.ElevatedButton(
                            "Поддержать нас 💰",
                            icon=ft.icons.PAYMENT,
                            on_click=self._open_donation_link,
                            style=ft.ButtonStyle(
                                bgcolor=ft.colors.GREEN,
                                color=ft.colors.WHITE,
                                padding=15
                            )
                        ),

                    ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                    border_radius=10,
                    margin=ft.margin.symmetric(horizontal=20, vertical=10)
                ),

                # Предложить книгу
                ft.Container(
                    content=ft.Column([
                        ft.Text("Предложить книгу", size=20, weight=ft.FontWeight.BOLD),
                        ft.Divider(),

                        ft.Text(
                            "Вы можете предложить интересующую вас книгу в нашем Telegram боте.",
                            text_align=ft.TextAlign.CENTER
                        ),

                        ft.ElevatedButton(
                            "Перейти в Telegram",
                            icon=ft.icons.TELEGRAM,
                            on_click=self._open_telegram_bot,
                            style=ft.ButtonStyle(
                                bgcolor=ft.colors.BLUE,
                                color=ft.colors.WHITE,
                                padding=15
                            )
                        ),

                    ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                    border_radius=10,
                    margin=ft.margin.symmetric(horizontal=20, vertical=10)
                ),



                # Лицензия и права
                ft.Container(
                    content=ft.Column([
                        ft.Text("Лицензия и права", size=20, weight=ft.FontWeight.BOLD),
                        ft.Divider(),

                        ft.Text(
                            "© 2026 NurBooks. Все права защищены.",
                            size=12,
                            color=ft.colors.GREY
                        ),

                        ft.Text(
                            "Приложение предназначено для некоммерческого использования. "
                            "Все книги предоставлены для ознакомительных целей.",
                            size=12,
                            color=ft.colors.GREY,
                            text_align=ft.TextAlign.JUSTIFY
                        ),

                    ], spacing=10),
                    padding=20,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                    border_radius=10,
                    margin=ft.margin.symmetric(horizontal=20, vertical=10)
                ),

                # Кнопка закрытия
                ft.Container(
                    content=ft.ElevatedButton(
                        "Закрыть",
                        icon=ft.icons.CLOSE,
                        on_click=self._on_close_click,
                        style=ft.ButtonStyle(padding=20)
                    ),
                    padding=ft.padding.all(20),
                    alignment=ft.alignment.center
                ),

            ], scroll=ft.ScrollMode.AUTO),
            expand=True
        )

    def _copy_to_clipboard(self, text: str):
        """Копирует текст в буфер обмена"""
        self.page.set_clipboard(text)
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Скопировано: {text}"),
            action="OK"
        )
        self.page.snack_bar.open = True
        self.page.update()


    def _on_close_click(self, e):
        """Обработчик кнопки закрытия"""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text("Выберите раздел в навигации слева"),
            action="OK",
            duration=2000,
        )
        self.page.snack_bar.open = True
        self.page.update()

    def _open_donation_link(self, e):
        """Открывает ссылку для доната"""
        webbrowser.open("https://www.donationalerts.com/r/nurapps")

    def _open_telegram_bot(self, e):
        """Открывает Telegram бота для предложения книги"""
        webbrowser.open("https://t.me/nurbooks_official_bot")
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text("Открыт Telegram бот для предложения книги"),
            action="OK",
            duration=3000,
        )
        self.page.snack_bar.open = True
        self.page.update()

    def build(self) -> ft.Control:
        """Возвращает содержимое страницы"""
        return self.content
