import webbrowser

import flet as ft


class BookProposalPage:
    def __init__(self, page: ft.Page, on_back=None):
        self.page = page
        self.on_back = on_back
        self.content = self._create_content()

    def _create_content(self) -> ft.Control:
        """Создает содержимое страницы предложения книги"""
        return ft.Container(
            content=ft.Column([
                # Заголовок
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.icons.ARROW_BACK,
                            on_click=self._on_back_click,
                            tooltip="Назад"
                        ),
                        ft.Text("Предложить книгу", size=24, weight=ft.FontWeight.BOLD),
                    ]),
                    padding=ft.padding.only(left=20, top=20, bottom=10)
                ),

                ft.Divider(),

                # Основной контент
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.LIGHTBULB_OUTLINE, size=48, color=ft.colors.PRIMARY),

                        ft.Text(
                            "Как предложить книгу?",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER
                        ),

                        ft.Container(height=10),

                        ft.Container(
                            content=ft.Column([
                                ft.Text("Чтобы предложить новую книгу в библиотеку, нужно:", size=14),
                                ft.Container(height=10),
                                _create_step_row("1", "Нажать кнопку ниже — откроется Telegram бот"),
                                _create_step_row("2", "Ответить на несколько вопросов бота"),
                                _create_step_row("3", "Дождаться проверки модератором"),
                                _create_step_row("4", "После одобрения книга появится в каталоге"),
                            ]),
                            bgcolor=ft.colors.SURFACE_VARIANT,
                            border_radius=12,
                            padding=20,
                        ),

                        ft.Container(height=10),

                        ft.Container(
                            content=ft.Column([
                                ft.Text("Что нужно знать:", size=16, weight=ft.FontWeight.BOLD),
                                ft.Container(height=5),
                                ft.Row([
                                    ft.Icon(ft.icons.CHECK_CIRCLE, size=16, color=ft.colors.GREEN),
                                    ft.Text("Книга должна быть на русском или английском языке", size=13, expand=True),
                                ], spacing=8),
                                ft.Row([
                                    ft.Icon(ft.icons.CHECK_CIRCLE, size=16, color=ft.colors.GREEN),
                                    ft.Text("Желательно указать автора и год издания", size=13, expand=True),
                                ], spacing=8),
                                ft.Row([
                                    ft.Icon(ft.icons.CHECK_CIRCLE, size=16, color=ft.colors.GREEN),
                                    ft.Text("Можно прикрепить ссылку на PDF (если есть)", size=13, expand=True),
                                ], spacing=8),
                                ft.Row([
                                    ft.Icon(ft.icons.INFO, size=16, color=ft.colors.BLUE),
                                    ft.Text("Процесс проверки обычно занимает 1-3 дня", size=13, expand=True),
                                ], spacing=8),
                            ]),
                            bgcolor=ft.colors.SURFACE_VARIANT,
                            border_radius=12,
                            padding=20,
                        ),

                        ft.Container(height=20),

                        # Кнопка для перехода в Telegram
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Перейти в Telegram бота",
                                icon=ft.icons.TELEGRAM,
                                on_click=self._open_telegram_bot,
                                style=ft.ButtonStyle(
                                    bgcolor=ft.colors.BLUE,
                                    color=ft.colors.WHITE,
                                    padding=ft.padding.symmetric(horizontal=30, vertical=15),
                                    text_style=ft.TextStyle(size=16),
                                )
                            ),
                            alignment=ft.alignment.center
                        ),

                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=0),
                    padding=ft.padding.symmetric(horizontal=40, vertical=20),
                    expand=True,
                ),

            ], scroll=ft.ScrollMode.AUTO),
            expand=True
        )

    def _open_telegram_bot(self, e):
        """Открывает Telegram бота для предложения книги"""
        webbrowser.open("https://t.me/nurbooks_official_bot")
        self.page.snack_bar = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.icons.TELEGRAM, color=ft.colors.WHITE),
                ft.Text("Telegram бот открыт. Ответьте на вопросы бота.", expand=True),
            ]),
            action="OK",
            duration=5000,
        )
        self.page.snack_bar.open = True
        self.page.update()

    def _on_back_click(self, e):
        """Обработчик кнопки назад"""
        if self.on_back:
            self.on_back()

    def build(self) -> ft.Control:
        """Возвращает содержимое страницы"""
        return self.content


def _create_step_row(num: str, text: str) -> ft.Control:
    """Создает строку шага с номером"""
    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Text(num, size=14, weight=ft.FontWeight.BOLD, color=ft.colors.PRIMARY),
                width=28,
                height=28,
                alignment=ft.alignment.center,
                bgcolor=ft.colors.PRIMARY_CONTAINER,
                border_radius=14,
            ),
            ft.Text(text, size=14, expand=True),
        ], spacing=12),
        margin=ft.margin.only(bottom=8),
    )
