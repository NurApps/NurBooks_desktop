import flet as ft
import webbrowser


class BookProposalPage:
    def __init__(self, page: ft.Page):
        self.page = page
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
                            tooltip="Назад к каталогу"
                        ),
                        ft.Text("Предложить книгу", size=24, weight=ft.FontWeight.BOLD),
                    ]),
                    padding=ft.padding.only(left=20, top=20, bottom=10)
                ),
                
                ft.Divider(),
                
                # Основной контент
                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            "Предложить книгу",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER
                        ),
                        
                        ft.Text(
                            "Вы можете предложить интересующую вас книгу в нашем Telegram боте.",
                            size=16,
                            text_align=ft.TextAlign.CENTER
                        ),
                        
                        ft.Divider(),
                        
                        ft.Text(
                            "В боте вам будут заданы вопросы для предложения книги. Формы больше нет — всё упрощено!",
                            size=14,
                            color=ft.colors.GREY_700,
                            text_align=ft.TextAlign.CENTER
                        ),
                        
                        # Кнопка для перехода в Telegram
                        ft.Container(
                            content=ft.ElevatedButton(
                                "Перейти в Telegram бота",
                                icon=ft.icons.TELEGRAM,
                                on_click=self._open_telegram_bot,
                                style=ft.ButtonStyle(
                                    bgcolor=ft.colors.BLUE,
                                    color=ft.colors.WHITE,
                                    padding=20
                                )
                            ),
                            padding=ft.padding.only(top=30),
                            alignment=ft.alignment.center
                        ),
                        
                    ], 
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20),
                    padding=ft.padding.all(30)
                ),
                
            ], scroll=ft.ScrollMode.AUTO),
            expand=True
        )

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

    def _on_back_click(self, e):
        """Обработчик кнопки назад"""
        # Вызываем метод главного приложения для возврата к каталогу
        # Это предполагает, что мы можем получить доступ к главному приложению
        # Но для простоты, просто вызовем метод, который обновит главное окно
        # через переданный callback
        from src.ui.pages.catalog_page import CatalogPage
        catalog_page = CatalogPage(
            page=self.page,
            on_book_click=lambda book: None  # временный хэндлер
        )
        parent_app = self._get_parent_app()
        if parent_app:
            parent_app._show_catalog_page()

    def _get_parent_app(self):
        """Пытается получить ссылку на главное приложение"""
        # Ищем в контролах страницы объект NurBooksApp
        for control in self.page.controls:
            if hasattr(control, 'controls') and len(control.controls) > 0:
                # Вложенные контролы
                for sub_control in control.controls:
                    if hasattr(sub_control, 'controls') and len(sub_control.controls) > 0:
                        for item in sub_control.controls:
                            if hasattr(item, 'controls') and len(item.controls) > 0:
                                for inner_item in item.controls:
                                    if hasattr(inner_item, 'controls') and len(inner_item.controls) > 0:
                                        for final_item in inner_item.controls:
                                            if hasattr(final_item, 'controls') and len(final_item.controls) > 0:
                                                for deepest_item in final_item.controls:
                                                    if hasattr(deepest_item, '_show_catalog_page'):
                                                        return deepest_item
        return None

    def build(self) -> ft.Control:
        """Возвращает содержимое страницы"""
        return self.content