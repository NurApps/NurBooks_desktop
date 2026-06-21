import flet as ft
import sys
import os
import threading
from typing import Optional

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.ui.pages.catalog_page import CatalogPage
from src.ui.pages.book_view import BookViewPage
from src.ui.pages.authors_page import AuthorsPage
from src.ui.pages.my_library import MyLibraryPage
from src.ui.pages.settings_page import SettingsPage
from src.ui.pages.about_page import AboutPage
from src.ui.pages.book_proposal_page import BookProposalPage
from src.ui.components.cart_widget import CartWidget
from src.ui.components.notifications_panel import NotificationsPanel
from src.core.notifications import NotificationManager
from src.ui.pages.pdf_reader import PDFReaderPage, on_app_exit
from src.core.storage import Storage
from src.core.downloader import Downloader
from src.core.models import Book
from src.config import APP_NAME, APP_VERSION

def resource_path(relative_path):
    """ Получение правильного пути к ресурсам """
    try:
        # Путь к ресурсам в PyInstaller
        base_path = getattr(sys, '_MEIPASS', None)
        if base_path is None:
            raise AttributeError("sys._MEIPASS not available")

    except Exception:
        # Путь к ресурсам в исходном коде
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
class NurBooksApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = f"{APP_NAME} v{APP_VERSION}"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0

        # Безопасная настройка окна для Flet 0.24.0
        # page.window может быть недоступен в некоторых режимах запуска.
        window = getattr(self.page, "window", None)
        if window is not None:
            window.width = 1200
            window.height = 800
            window.min_width = 800
            window.min_height = 600


        # Инициализация менеджеров
        self.notification_manager = NotificationManager()
        self.storage = Storage()
        self.downloader = Downloader(database=self.storage.database)
        
        # Загрузка настроек
        self.settings = self.storage.load_settings()
        self.notification_manager.set_sound_enabled(getattr(self.settings, "sound_notifications", True))
        self.notification_manager.set_enabled(getattr(self.settings, "background_notifications", True))
        if self.settings.theme == "dark":
            self.page.theme_mode = ft.ThemeMode.DARK
        
        # Состояние приложения
        self.current_page = "catalog"
        self.selected_book = None
        self.selected_author = None
        
        # Инициализация корзины
        self.cart_widget = CartWidget(
            on_download_all=self._on_cart_download,
            on_remove_item=self._on_cart_remove,
            on_close=self._close_cart
        )
        self.cart_visible = False
        
        # Создание навигации
        self.nav_rail = self._create_navigation_rail()
        self.notification_panel = self._create_notification_panel()
        self.top_app_bar = self._create_top_app_bar()
        
        # Основной контейнер
        self.main_content = ft.Container(expand=True)
        
        # Контейнер для панели уведомлений
        self.notification_panel_container = ft.Container(
            content=self.notification_panel,
            width=350,
            visible=False,
            bgcolor=ft.colors.BACKGROUND
        )
        
        # Контейнер для корзины
        self.cart_container = ft.Container(
            content=self.cart_widget.build(),
            right=20,
            bottom=20,
            visible=False,
            animate_position=ft.animation.Animation(300, ft.AnimationCurve.EASE_IN_OUT)
        )
        
        # Инициализация начальной страницы
        self._show_catalog_page()
        
        # Создание основного макета
        self.page.add(
            ft.Column([
                # Верхняя панель
                self.top_app_bar,
                
                # Основная область
                ft.Stack([
                    ft.Row([
                        # Навигационная панель
                        ft.Container(
                            content=self.nav_rail,
                            width=95,
                            bgcolor=ft.colors.SURFACE_VARIANT
                        ),
                        
                        # Основное содержимое
                        ft.Container(
                            content=self.main_content,
                            expand=True
                        ),
                        
                        # Панель уведомлений (скрыта по умолчанию)
                        self.notification_panel_container,
                    ], expand=True),
                    
                    # Корзина (поверх основного содержимого)
                    self.cart_container
                ], expand=True),
            ], expand=True)
        )

    
    def _on_window_event(self, e):
        """Обработчик событий окна - очищает временные файлы при закрытии"""
        if e.data == "close":
            # Очищаем все временные PDF файлы
            on_app_exit()
            self.page.window.close()
    
    def _create_top_app_bar(self) -> ft.Control:
        """Создает верхнюю панель приложения"""
        return ft.Container(
            content=ft.Row([
                # Логотип и название
                ft.Row([
                    ft.Image(
                        src="assets/logo.ico" if self.page.theme_mode == ft.ThemeMode.LIGHT else "assets/logo.ico",
                        width=40,
                        height=40,
                        fit=ft.ImageFit.CONTAIN,
                        border_radius=20,
                    ),
                    ft.Text(APP_NAME, size=20, weight=ft.FontWeight.BOLD),
                ]),
                
                ft.Container(expand=True),
                
                # Кнопки действий
                ft.Row([
                    # Кнопка уведомлений с бейджем
                    ft.Stack([
                        ft.IconButton(
                            icon=ft.icons.NOTIFICATIONS,
                            tooltip="Уведомления",
                            on_click=self._toggle_notification_panel,
                            icon_color=ft.colors.PRIMARY
                        ),
                        ft.Container(
                            content=ft.Text(
                                "0",
                                size=10,
                                color=ft.colors.WHITE,
                                weight=ft.FontWeight.BOLD
                            ),
                            padding=2,
                            bgcolor=ft.colors.RED,
                            border_radius=10,
                            width=20,
                            height=20,
                            alignment=ft.alignment.center,
                            visible=False,
                            top=5,
                            right=5,
                            key="notification_badge"
                        )
                    ]),
                    
                    # Кнопка корзины с бейджем
                    ft.Stack([
                        ft.IconButton(
                            icon=ft.icons.SHOPPING_CART,
                            tooltip="Корзина",
                            on_click=self._toggle_cart,
                            icon_color=ft.colors.PRIMARY
                        ),
                        ft.Container(
                            content=ft.Text(
                                "0",
                                size=10,
                                color=ft.colors.WHITE,
                                weight=ft.FontWeight.BOLD
                            ),
                            padding=2,
                            bgcolor=ft.colors.RED,
                            border_radius=10,
                            width=20,
                            height=20,
                            alignment=ft.alignment.center,
                            visible=False,
                            top=5,
                            right=5,
                            key="cart_badge"
                        )
                    ]),
                    
                    # Кнопка темы
                    ft.IconButton(
                        icon=ft.icons.BRIGHTNESS_4,
                        tooltip="Сменить тему",
                        on_click=self._toggle_theme,
                        icon_color=ft.colors.PRIMARY
                    ),
                    ft.IconButton(
                        icon=ft.icons.EXIT_TO_APP,
                        tooltip="Выйти из приложения",
                        on_click=self._exit_app,
                        icon_color=ft.colors.PRIMARY
                    ),
                ], spacing=10),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            bgcolor=ft.colors.SURFACE_VARIANT,
            border=ft.border.only(bottom=ft.border.BorderSide(1, ft.colors.OUTLINE))
        )
    
    def _create_navigation_rail(self) -> ft.NavigationRail:
        """Создает навигационную панель"""
        return ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=95,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.icons.BOOK,
                    selected_icon=ft.icons.BOOK,
                    label="Каталог"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.PERSON,
                    selected_icon=ft.icons.PERSON,
                    label="Авторы"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.BOOKMARK,
                    selected_icon=ft.icons.BOOKMARK,
                    label="Моя библиотека"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.RECOMMEND,
                    selected_icon=ft.icons.RECOMMEND,
                    label="Предложить книгу"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.SETTINGS,
                    selected_icon=ft.icons.SETTINGS,
                    label="Настройки"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.INFO,
                    selected_icon=ft.icons.INFO,
                    label="О приложении"
                ),
            ],
            on_change=self._on_navigation_change
        )
    
    def _create_notification_panel(self) -> ft.Control:
        """Создает панель уведомлений"""
        self.notifications_component = NotificationsPanel(
            on_clear_all=self._clear_all_notifications,
            on_notification_click=self._remove_notification,
            on_notification_detail=self._show_notification_detail
        )

        self.notification_list_container = ft.Container(expand=True)

        self._update_notification_panel()

        return ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.IconButton(
                        icon=ft.icons.CLOSE,
                        on_click=self._toggle_notification_panel
                    ),
                    ft.Text("Уведомления", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.TextButton(
                        "Очистить все",
                        on_click=self._clear_all_notifications
                    ),
                ]),
                padding=10,
                bgcolor=ft.colors.SURFACE_VARIANT
            ),
            ft.Divider(height=1),
            self.notification_list_container,
        ])

    def _update_notification_panel(self):
        """Обновляет панель уведомлений"""
        unread_count = self.notification_manager.get_unread_count()
        self.notifications_component.set_notifications(
            self.notification_manager.get_notifications(),
            unread_count
        )
        if hasattr(self, 'notification_list_container'):
            self.notification_list_container.content = self.notifications_component.build()
        self._update_notification_badge()
    
    def _update_notification_badge(self):
        """Обновляет бейдж уведомлений"""
        unread_count = self.notification_manager.get_unread_count()
        # Находим бейдж в top_app_bar и обновляем
        if hasattr(self, 'top_app_bar') and hasattr(self.top_app_bar, 'content'):
            # Обновляем через перебор элементов
            self._update_badge_in_container(self.top_app_bar, unread_count)
    
    def _update_badge_in_container(self, container, count):
        """Рекурсивно находит и обновляет бейдж уведомлений"""
        try:
            if hasattr(container, 'key') and container.key == "notification_badge":
                container.content.value = str(count) if count < 100 else "99+"
                container.visible = count > 0
                if count >= 10:
                    container.width = None
                    container.padding = ft.padding.symmetric(horizontal=4)
                return True
            
            if hasattr(container, 'content'):
                if isinstance(container.content, (list, tuple)):
                    for item in container.content:
                        if self._update_badge_in_container(item, count):
                            return True
                elif self._update_badge_in_container(container.content, count):
                    return True
            
            if hasattr(container, 'controls'):
                for control in container.controls:
                    if self._update_badge_in_container(control, count):
                        return True
            
            if hasattr(container, 'rows'):
                for row in container.rows:
                    if self._update_badge_in_container(row, count):
                        return True
        except Exception:
            pass
        return False
    
    def _update_cart_badge(self):
        """Обновляет бейдж корзины"""
        cart_count = len(self.cart_widget.get_all_books())
        # Этот метод устарел, так как он обновлял бейдж уведомлений.
        # Вместо этого, используйте _update_badge_in_container для корзины.
        # self._update_badge_in_container(self.top_app_bar, cart_count) # Это неверно
    
        # Ищем и обновляем бейдж корзины
        if hasattr(self, 'top_app_bar') and hasattr(self.top_app_bar, 'content'):
            self._update_cart_badge_in_container(self.top_app_bar, cart_count)

    def _update_cart_badge_in_container(self, container, count):
        """Рекурсивно находит и обновляет бейдж корзины"""
        try:
            if hasattr(container, 'key') and container.key == "cart_badge":
                container.content.value = str(count) if count < 100 else "99+"
                container.visible = count > 0
                if count >= 10:
                    container.width = None
                    container.padding = ft.padding.symmetric(horizontal=4)
                return True

            if hasattr(container, 'content'):
                if isinstance(container.content, (list, tuple)):
                    for item in container.content:
                        if self._update_cart_badge_in_container(item, count):
                            return True
                elif self._update_cart_badge_in_container(container.content, count):
                    return True

            if hasattr(container, 'controls'):
                for control in container.controls:
                    if self._update_cart_badge_in_container(control, count):
                        return True

            if hasattr(container, 'rows'):
                for row in container.rows:
                    if self._update_cart_badge_in_container(row, count):
                        return True
        except Exception:
            pass
        return False

    def _on_notifications_click(self, e=None):
        """Обработчик кнопки уведомлений"""
        self._toggle_notification_panel(e)

    def _toggle_notification_panel(self, e=None):
        """Показывает/скрывает панель уведомлений"""
        if self.notification_panel_container.visible:
            self.notification_panel_container.visible = False
        else:
            self._update_notification_panel()
            self.notification_panel_container.visible = True
            # Отмечаем уведомления как прочитанные
            self.notification_manager.mark_as_read()
            # Скрываем корзину если она открыта
            if self.cart_visible:
                self._toggle_cart(update_ui=False)
        self._update_notification_badge()
        self.page.update()

    def _toggle_cart(self, e=None, update_ui: bool = True):
        """Показывает/скрывает корзину"""
        self.cart_visible = not self.cart_visible
        self.cart_container.visible = self.cart_visible
        
        # Обновляем содержимое корзины
        if self.cart_visible:
            self.cart_widget._update_cart()
            # Скрываем панель уведомлений если она открыта
            if self.notification_panel_container.visible:
                self.notification_panel_container.visible = False
        self._update_cart_badge()
        if update_ui:
            self.page.update()
    
    def _close_cart(self, e=None, update_ui: bool = True):
        """Закрывает корзину"""
        self.cart_visible = False
        self.cart_container.visible = False
        self._update_cart_badge()
        if update_ui:
            self.page.update()
    
    def _toggle_theme(self, e=None):
        """Переключает тему"""
        if self.page.theme_mode == ft.ThemeMode.LIGHT:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.settings.theme = "dark"
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.settings.theme = "light"
        
        self.storage.save_settings(self.settings)
        self.page.update()
    
    def _clear_all_notifications(self, e=None):
        """Очищает все уведомления"""
        self.notification_manager.clear_notifications()
        self._update_notification_panel()
        self.page.update()
    
    def _remove_notification(self, notification_id: int):
        """Удаляет конкретное уведомление"""
        self.notification_manager.remove_notification(notification_id)
        self._update_notification_panel()
        self.page.update()
    
    def _show_notification_detail(self, notification):
        """Показывает детальное окно уведомления"""
        from src.ui.components.notifications_panel import NotificationDetailDialog
        
        detail_dialog = NotificationDetailDialog(
            notification=notification,
            on_close=self._close_notification_dialog,
            on_delete=self._delete_notification_from_detail
        )
        self.active_notification_dialog = detail_dialog.build()
        self.page.open(self.active_notification_dialog)
    
    def _close_notification_dialog(self, e=None):
        """Закрывает диалоговое окно уведомления"""
        if hasattr(self, 'active_notification_dialog') and self.active_notification_dialog:
            self.page.close(self.active_notification_dialog)
            self.active_notification_dialog = None
    
    def _delete_notification_from_detail(self, notification_id: int):
        """Удаляет уведомление из детального просмотра"""
        self._close_notification_dialog()
        self.notification_manager.remove_notification(notification_id)
        self._update_notification_panel()
        self.page.update()
    
    def _update_notifications(self, e=None):
        """Обновляет уведомления"""
        self._update_notification_panel()
        self.page.update()
    
    def _on_navigation_change(self, e):
        """Обработчик изменения навигации"""
        index = e.control.selected_index

        if index == 0:
            self._show_catalog_page(update_ui=False)
        elif index == 1:
            self._show_authors_page(update_ui=False)
        elif index == 2:
            self._show_my_library_page(update_ui=False)
        elif index == 3:
            self._show_book_proposal_form(update_ui=False)
        elif index == 4:
            self._show_settings_page(update_ui=False)
        elif index == 5:
            self._show_about_page(update_ui=False)

        self.nav_rail.selected_index = index
        self.page.update()
    
    def _show_catalog_page(self, update_ui: bool = True):
        """Показывает страницу каталога"""
        catalog_page = CatalogPage(
            page=self.page,
            on_book_click=self._on_book_selected
        )
        self.main_content.content = catalog_page.build()
        self.current_page = "catalog"
        if update_ui:
            self.page.update()

    def _show_book_proposal_form(self, update_ui: bool = True):
        """Открывает Telegram бота для предложения книги"""
        import webbrowser
        
        # Открываем бота
        webbrowser.open("https://t.me/nurbooks_official_bot")
        
        # Показываем уведомление
        self.notification_manager.add_notification(
            title="Открыт бот",
            message="В боте вам будут заданы вопросы для предложения книги. Формы больше нет — всё упрощено!",
            type="success"
        )
        
        if update_ui:
            self.page.update()
    
    def _show_authors_page(self, update_ui: bool = True):
        """Показывает страницу авторов"""
        authors_page = AuthorsPage(
            page=self.page,
            on_author_click=self._on_author_selected
        )
        self.main_content.content = authors_page.build()
        self.current_page = "authors"
        if update_ui:
            self.page.update()
    
    def _show_my_library_page(self, update_ui: bool = True):
        """Показывает страницу моей библиотеки"""
        library_page = MyLibraryPage(
            page=self.page,
            notification_manager=self.notification_manager,
            on_read_book=self._show_pdf_reader
        )
        self.main_content.content = library_page.build()
        self.current_page = "library"
        if update_ui:
            self.page.update()
    
    def _show_settings_page(self, update_ui: bool = True):
        """Показывает страницу настроек"""
        settings_page = SettingsPage(
            page=self.page,
            notification_manager=self.notification_manager
        )
        self.main_content.content = settings_page.build()
        self.current_page = "settings"
        if update_ui:
            self.page.update()
    
    def _show_about_page(self, update_ui: bool = True):
        """Показывает страницу о приложении"""
        about_page = AboutPage(page=self.page)
        self.main_content.content = about_page.build()
        self.current_page = "about"
        if update_ui:
            self.page.update()
    
    def _exit_app(self, e=None):
        """Корректный выход из приложения."""
        try:
            on_app_exit()
        finally:
            if getattr(self.page, "window", None):
                self.page.window.close()

    def _on_book_selected(self, book: Book):
        """Обработчик выбора книги"""
        self.selected_book = book
        from src.core.statistics_manager import stats        
        stats.increment_view_count(book.id)
        book.view_count = getattr(book, "view_count", 0) + 1

        # Проверяем, скачана ли книга
        is_downloaded, _ = self.downloader.is_book_downloaded(book) if book else (False, None)

        # Показываем диалог с выбором действия
        dlg = ft.AlertDialog(
            title=ft.Text(book.title, text_align=ft.TextAlign.CENTER),
            content=ft.Column([
                ft.Image(
                    src=book.cover if book.cover else "assets/logo.png",
                    width=100,
                    height=150,
                    fit=ft.ImageFit.COVER,
                    border_radius=5
                ),
                ft.Text(f"Автор: {book.author}", text_align=ft.TextAlign.CENTER),
                ft.Text(f"Категория: {book.category}", text_align=ft.TextAlign.CENTER),
                ft.Divider(),
                ft.Text("Выберите действие:", text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            actions=[
                ft.Row([
                    ft.TextButton(
                        "Просмотреть",
                        icon=ft.icons.VISIBILITY,
                        on_click=lambda e: self._open_book_view(book, dlg),
                        expand=True
                    ),
                    ft.TextButton(
                        "Читать",
                        icon=ft.icons.MENU_BOOK,
                        on_click=lambda e: self._show_pdf_reader(book, dlg),
                        expand=True,
                        visible=is_downloaded
                    ),
                    ft.TextButton(
                        "Инфо",
                        icon=ft.icons.INFO,
                        on_click=lambda e: self._show_book_info_dialog(book, dlg),
                        expand=True,
                        visible=not is_downloaded
                    ),
                    ft.TextButton(
                        "В корзину",
                        icon=ft.icons.ADD_SHOPPING_CART,
                        on_click=lambda e: self._add_to_cart(book, dlg),
                        expand=True
                    ),
                    ft.TextButton(
                        "Выйти",
                        icon=ft.icons.CLOSE,
                        on_click=lambda _: self.page.close(dlg),
                        expand=True
                    ),
                ], spacing=5)
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER
        )
        self.page.open(dlg)
        self.page.update()

    def _show_book_info_dialog(self, book: Book, parent_dlg: Optional[ft.AlertDialog] = None):
        """Показывает диалог с информацией о том как читать книгу"""
        if parent_dlg:
            self.page.close(parent_dlg)
            
        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.INFO, color=ft.colors.PRIMARY),
                ft.Text("Как читать книгу")
            ]),
            content=ft.Column([
                ft.Text(f"Книга: '{book.title}'", weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Чтобы читать книгу, её нужно сначала скачать.", size=16),
                ft.Divider(),
                ft.Text("После скачивания вы сможете читать:", weight=ft.FontWeight.BOLD),
                ft.Column([
                    ft.Row([
                        ft.Icon(ft.icons.CHECK, color=ft.colors.GREEN, size=16),
                        ft.Text("Во встроенной читалке NurBooks")
                    ]),
                    ft.Row([
                        ft.Icon(ft.icons.CHECK, color=ft.colors.GREEN, size=16),
                        ft.Text("В системной программе для PDF")
                    ]),
                ], spacing=5),
                ft.Divider(),
                ft.Text("Нажмите кнопку 'Скачать' чтобы начать.", weight=ft.FontWeight.BOLD),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("Понятно", on_click=lambda _: self.page.close(dlg)),
                ft.ElevatedButton(
                    "Скачать",
                    icon=ft.icons.DOWNLOAD,
                    on_click=lambda _: self._close_book_dialog_and_download(book, dlg)
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)
        self.page.update()

    def _close_book_dialog_and_download(self, book: Book, dlg):
        """Закрывает диалог и начинает скачивание"""
        self.page.close(dlg)

        def download():
            try:
                self.downloader.download_book(book)
                from src.core.statistics_manager import stats
                stats.increment_download_count(book.id)
                book.download_count = getattr(book, "download_count", 0) + 1
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"✅ Книга '{book.title}' скачана!"),
                    action="OK"
                )
                self.page.snack_bar.open = True
                self.page.update()
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"❌ Ошибка скачивания: {ex}"),
                    bgcolor=ft.colors.ERROR
                )
                self.page.snack_bar.open = True
                self.page.update()

        threading.Thread(target=download, daemon=True).start()    

    def _open_book_view(self, book: Book, dlg: Optional[ft.AlertDialog] = None):
        """Открывает страницу просмотра книги"""
        if dlg:
            self.page.close(dlg)

        book_page = BookViewPage(
            page=self.page,
            book=book,
            notification_manager=self.notification_manager,
            cart_widget=self.cart_widget,
            on_back=self._show_catalog_page,
            on_read=self._show_pdf_reader
        )
        self.main_content.content = book_page.build()
        self.page.update()
    
    def _show_pdf_reader(self, book: Book, page_number: Optional[int] = None, dlg: Optional[ft.AlertDialog] = None):
        """Открывает встроенную читалку PDF"""
        from src.core.database import Database
        if dlg:
            self.page.close(dlg)
        
        # Получаем закладки для этой книги
        db = Database()
        reader = PDFReaderPage(
            page=self.page,
            book=book,
            on_back=lambda: self._open_book_view(book),
            downloader=self.downloader,
            bookmarks=db.get_bookmarks_by_book(book.id),
            go_to_page=page_number
        )
        self.main_content.content = reader.build()
        self.page.update()
        
    def _add_to_cart(self, book: Book, dlg: Optional[ft.AlertDialog] = None):
        """Добавляет книгу в корзину"""
        if dlg:
            self.page.close(dlg)
        
        if self.cart_widget.add_book(book):
            self.notification_manager.add_notification(
                title="Книга добавлена",
                message=f"Книга '{book.title}' добавлена в корзину",
                type="success"
            )
            
            # Показываем корзину, если она не видна
            if not self.cart_visible:
                self._toggle_cart(update_ui=False)
            
            self._update_notification_panel()
            self._update_cart_badge()
            self.page.update()
        else:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Эта книга уже в корзине"),
                action="OK"
            )
            self.page.snack_bar.open = True
            self.page.update()
    
    def _on_cart_download(self, books: list):
        """Скачивание книг из корзины"""
        def download_all():
            for book in books:
                try:
                    _, formatted_size = self.downloader.download_book_with_size(book)
                    from src.core.statistics_manager import stats
                    stats.increment_download_count(book.id)
                    book.download_count = getattr(book, "download_count", 0) + 1

                    # Обновляем размер файла в базе данных
                    self.storage.database.update_book_file_size(book.id, formatted_size)

                    self.notification_manager.add_notification(
                        title="Книга скачана",
                        message=f"Книга '{book.title}' успешно скачана ({formatted_size})",
                        type="success"
                    )

                    # Удаляем книгу из корзины после скачивания
                    self.cart_widget.remove_book(book.id)

                except Exception as e:
                    self.notification_manager.add_notification(
                        title="Ошибка скачивания",
                        message=f"Не удалось скачать '{book.title}': {str(e)}",
                        type="error"
                    )
            
            self._update_notification_panel()
            self._update_cart_badge()
            
            # Показываем сообщение об успешном скачивании
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Скачано {len(books)} книг"),
                action="OK"
            )
            self.page.snack_bar.open = True
            self.page.update()

        threading.Thread(target=download_all, daemon=True).start()
          
    def _on_cart_remove(self, book_id: int):
        """Удаление книги из корзины"""
        self.cart_widget.remove_book(book_id)
        
        self.notification_manager.add_notification(
            title="Книга удалена",
            message="Книга удалена из корзины",
            type="info"
        )
        
        self._update_notification_panel()
        self._update_cart_badge()
        self.page.update()
    
    def _on_author_selected(self, author):
        """Обработчик выбора автора"""
        self.selected_author = author
        
        # Показываем книги автора
        storage = Storage()
        books = storage.load_books()
        
        # Фильтруем книги по автору
        author_books = [book for book in books if book.id in author.books]
        
        # Создаем кастомную страницу с книгами автора
        content = ft.Container(
            content=ft.Column([
                # Заголовок
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.icons.ARROW_BACK,
                            on_click=lambda e: self._show_authors_page()
                        ),
                        ft.Text(f"Книги автора: {author.name}", size=24, weight=ft.FontWeight.BOLD),
                    ]),
                    padding=ft.padding.only(left=20, top=20, bottom=10)
                ),
                
                # Биография
                ft.Container(
                    content=ft.Column([
                        ft.Text("Биография", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(author.bio, text_align=ft.TextAlign.JUSTIFY),
                    ]),
                    padding=20,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                    border_radius=10,
                    margin=ft.margin.symmetric(horizontal=20, vertical=10)
                ),
                
                # Книги автора
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Книги ({len(author_books)})", size=18, weight=ft.FontWeight.BOLD),
                        ft.Divider(),
                        
                        ft.GridView(
                            controls=[
                                self._create_simple_book_card(book)
                                for book in author_books
                            ],
                            max_extent=200,
                            child_aspect_ratio=0.8,
                            spacing=15,
                            run_spacing=15,
                            padding=20,
                            expand=True
                        ),
                    ]),
                    expand=True
                ),
            ], scroll=ft.ScrollMode.AUTO),
            expand=True
        )
        
        self.main_content.content = content
        self.page.update()
    
    def _create_simple_book_card(self, book):
        """Создает простую карточку книги"""
        return ft.Container(
            content=ft.Column([
                ft.Image(
                    src=book.cover if book.cover else "assets/logo.png",
                    width=150,
                    height=200,
                    fit=ft.ImageFit.COVER,
                    border_radius=ft.border_radius.all(5),
                ),
                ft.Text(
                    book.title,
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    text_align=ft.TextAlign.CENTER
                ),
            ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=180,
            height=260,
            padding=10,
            bgcolor=ft.colors.SURFACE_VARIANT,
            border_radius=10,
            on_click=lambda e, b=book: self._on_book_selected(b),
            tooltip=book.title,
            ink=True,
        )
def main(page: ft.Page):
    NurBooksApp(page)

if __name__ == "__main__":
    ft.app(target=main, assets_dir=resource_path(""))
