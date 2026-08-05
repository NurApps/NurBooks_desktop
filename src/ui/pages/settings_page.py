import os

import flet as ft

from src.config import APP_VERSION, NURBOOKS_DOWNLOADS_PATH
from src.core.models import UserSettings
from src.core.notifications import NotificationManager
from src.core.storage import Storage


class SettingsPage:
    def __init__(
        self, page: ft.Page, notification_manager: NotificationManager | None = None
    ):
        self.page = page
        self.notification_manager = notification_manager
        self.storage = Storage()
        self.settings = self.storage.load_settings()

        # Создаем элементы интерфейса
        self.download_path_field = ft.TextField(
            label="Путь для скачивания", value=self.settings.default_path, expand=True
        )

        self.theme_dropdown = ft.Dropdown(
            label="Тема интерфейса",
            value=self.settings.theme or "light",
            options=[
                ft.dropdown.Option("light", "Светлая"),
                ft.dropdown.Option("dark", "Темная"),
            ],
            width=200,
            on_change=self._on_theme_change,
        )

        self.language_dropdown = ft.Dropdown(
            label="Язык интерфейса",
            value=self.settings.language or "ru",
            options=[
                ft.dropdown.Option("ru", "Русский"),
            ],
            width=200,
        )

        self.pdf_reader_dropdown = ft.Dropdown(
            label="PDF-читалка по умолчанию",
            value=getattr(self.settings, "pdf_reader", "ask") or "ask",
            options=[
                ft.dropdown.Option("ask", "Спрашивать каждый раз"),
                ft.dropdown.Option("builtin", "Встроенная читалка"),
                ft.dropdown.Option("system", "Системная программа"),
            ],
            width=250,
            hint_text="Как открывать PDF книги",
        )



        # Переключатели уведомлений
        self.download_notifications_switch = ft.Switch(
            label="Показывать уведомления о скачивании",
            value=getattr(self.settings, "download_notifications", True)
        )
        self.sound_notifications_switch = ft.Switch(
            label="Звуковые уведомления",
            value=getattr(self.settings, "sound_notifications", True)
        )
        self.update_notifications_switch = ft.Switch(
            label="Уведомления об обновлениях",
            value=getattr(self.settings, "update_notifications", True)
        )
        self.background_notifications_switch = ft.Switch(
            label="Фоновые уведомления",
            value=getattr(self.settings, "background_notifications", True)
        )

        # Обновления
        self.auto_update_switch = ft.Switch(
            label="Автоматически проверять обновления",
            value=getattr(self.settings, "auto_update", False),
        )
        self.beta_updates_switch = ft.Switch(
            label="Участвовать в бета-тестировании",
            value=getattr(self.settings, "beta_updates", False),
        )
        self._update_status_text = ft.Text("", size=12, color=ft.colors.GREY_700)
        self._check_update_btn = ft.ElevatedButton(
            "Проверить обновления",
            icon=ft.icons.UPDATE,
            on_click=self._on_check_updates,
        )

        # Элементы для настроек облака Firebase
        self.cloudflare_api_token_field = ft.TextField(
            label="Cloudflare API Token",
            value=getattr(self.settings, "cloudflare_api_token", ""),
            password=True,
            can_reveal_password=True,
        )

        # Аккаунт
        self._account_status_text = ft.Text("", size=13)
        self._login_btn = ft.ElevatedButton(
            "Войти",
            icon=ft.icons.LOGIN,
            on_click=self._show_login_dialog,
        )
        self._logout_btn = ft.OutlinedButton(
            "Выйти",
            icon=ft.icons.LOGOUT,
            on_click=self._on_logout,
            visible=False,
        )
        self._register_btn = ft.OutlinedButton(
            "Регистрация",
            icon=ft.icons.APP_REGISTRATION,
            on_click=self._show_register_dialog,
            visible=False,
        )
        self._email_field = ft.TextField(label="Ник или Email", autofocus=True, keyboard_type=ft.KeyboardType.EMAIL)
        self._password_field = ft.TextField(
            label="Пароль", password=True, can_reveal_password=True,
            on_submit=self._on_login_submit,
        )
        self._login_status_text = ft.Text("", size=12)
        self._login_progress = ft.ProgressRing(width=18, height=18, visible=False)
        self._register_nickname_field = ft.TextField(label="Ник", autofocus=True)
        self._register_password_field = ft.TextField(
            label="Пароль", password=True, can_reveal_password=True,
            on_submit=self._on_register_submit,
        )
        self._register_status_text = ft.Text("", size=12)
        self._register_progress = ft.ProgressRing(width=18, height=18, visible=False)
        self._update_account_section()

        # Создаем основное содержимое
        self.content = ft.Container(
            content=ft.Column(
                [
                    # Аккаунт
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Аккаунт", size=20, weight=ft.FontWeight.BOLD),
                                ft.Divider(),
                                self._account_status_text,
                                ft.Row(
                                    [
                                        self._login_btn,
                                        self._logout_btn,
                                        self._register_btn,
                                    ],
                                    spacing=10,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=20,
                        bgcolor=ft.colors.SURFACE_VARIANT,
                        border_radius=10,
                        margin=ft.margin.symmetric(horizontal=20, vertical=10),
                    ),

                    # Основные настройки
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Основные настройки",
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Divider(),
                                # Путь для скачивания
                                ft.Row(
                                    [
                                        self.download_path_field,
                                        ft.IconButton(
                                            icon=ft.icons.FOLDER_OPEN,
                                            tooltip="Выбрать папку",
                                            on_click=self._on_select_folder,
                                        ),
                                    ]
                                ),
                                # Тема и язык
                                ft.Row(
                                    [
                                        self.theme_dropdown,
                                        self.language_dropdown,
                                    ],
                                    spacing=20,
                                ),
                            ],
                            spacing=15,
                        ),
                        padding=20,
                        bgcolor=ft.colors.SURFACE_VARIANT,
                        border_radius=10,
                        margin=ft.margin.symmetric(horizontal=20, vertical=10),
                    ),
                    # Настройки чтения
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Настройки чтения",
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Divider(),
                                ft.Row(
                                    [
                                        ft.Icon(ft.icons.MENU_BOOK, size=20),
                                        self.pdf_reader_dropdown,
                                    ],
                                    spacing=10,
                                ),
                                ft.Text(
                                    "Встроенная читалка NurBooks позволяет читать книги прямо в приложении по старой схеме : скачал и читаешь.",
                                    size=12,
                                    color=ft.colors.GREY_700,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=20,
                        bgcolor=ft.colors.SURFACE_VARIANT,
                        border_radius=10,
                        margin=ft.margin.symmetric(horizontal=20, vertical=10),
                    ),
                    # Настройки уведомлений
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Уведомления", size=20, weight=ft.FontWeight.BOLD
                                ),
                                ft.Divider(),
                                self.download_notifications_switch,
                                self.sound_notifications_switch,
                                self.update_notifications_switch,
                                self.background_notifications_switch,
                            ],
                            spacing=10,
                        ),
                        padding=20,
                        bgcolor=ft.colors.SURFACE_VARIANT,
                        border_radius=10,
                        margin=ft.margin.symmetric(horizontal=20, vertical=10),
                    ),
                    # Обновления
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Обновления", size=20, weight=ft.FontWeight.BOLD),
                                ft.Divider(),
                                self.auto_update_switch,
                                self.beta_updates_switch,
                                ft.Row(
                                    [self._check_update_btn, self._update_status_text],
                                    spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=20,
                        bgcolor=ft.colors.SURFACE_VARIANT,
                        border_radius=10,
                        margin=ft.margin.symmetric(horizontal=20, vertical=10),
                    ),
                    # Кэш и данные
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Данные и кэш", size=20, weight=ft.FontWeight.BOLD
                                ),
                                ft.Divider(),
                                ft.Row(
                                    [
                                        ft.Text("Размер кэша обложек:"),
                                        ft.Text("5.2 MB", weight=ft.FontWeight.BOLD),
                                        ft.Container(expand=True),
                                        ft.TextButton(
                                            "Очистить кэш",
                                            on_click=self._on_clear_cache,
                                        ),
                                    ]
                                ),
                                ft.Row(
                                    [
                                        ft.Text("Размер скачанных книг:"),
                                        ft.Text(
                                            self._get_downloaded_size(),
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Container(expand=True),
                                        ft.TextButton(
                                            "Показать папку",
                                            on_click=self._on_show_folder,
                                        ),
                                    ]
                                ),
                                ft.Divider(),
                                ft.Row(
                                    [
                                        ft.Text("Экспорт данных:"),
                                        ft.Container(expand=True),
                                        ft.ElevatedButton(
                                            "Экспортировать в JSON",
                                            icon=ft.icons.DOWNLOAD,
                                            on_click=self._on_export_data,
                                        ),
                                    ]
                                ),
                            ],
                            spacing=10,
                        ),
                        padding=20,
                        bgcolor=ft.colors.SURFACE_VARIANT,
                        border_radius=10,
                        margin=ft.margin.symmetric(horizontal=20, vertical=10),
                    ),
                    # Кнопки действий
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.ElevatedButton(
                                    "Сохранить настройки",
                                    icon=ft.icons.SAVE,
                                    on_click=self._on_save_settings,
                                    style=ft.ButtonStyle(padding=20),
                                ),
                                ft.OutlinedButton(
                                    "Сбросить настройки",
                                    icon=ft.icons.RESTORE,
                                    on_click=self._on_reset_settings,
                                    style=ft.ButtonStyle(padding=20),
                                ),
                            ],
                            spacing=20,
                        ),
                        padding=ft.padding.all(20),
                        alignment=ft.alignment.center,
                    ),
                    # Информация о приложении
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "О приложении", size=20, weight=ft.FontWeight.BOLD
                                ),
                                ft.Divider(),
                                ft.Text(f"Версия: {APP_VERSION}", size=12),
                            ]
                        ),
                        padding=20,
                        bgcolor=ft.colors.SURFACE_VARIANT,
                        border_radius=10,
                        margin=ft.margin.symmetric(horizontal=20, vertical=10),
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )

    def _on_check_updates(self, e):
        """Проверяет обновления на GitHub."""
        from src.config import APP_VERSION as CURR_VER
        from src.core.updater import check_latest, is_newer

        self._check_update_btn.disabled = True
        self._update_status_text.value = "Проверка..."
        self._update_status_text.color = ft.colors.GREY_700
        self.page.update()

        def _done(info):
            self._check_update_btn.disabled = False
            if info and is_newer(CURR_VER, info.version):
                self._update_status_text.value = f"Доступна версия {info.version}!"
                self._update_status_text.color = ft.colors.GREEN
                self.page.update()

                dlg = ft.AlertDialog(
                    title=ft.Text("Доступно обновление"),
                    content=ft.Text(
                        f"Версия {info.version} доступна для скачивания.\n\n"
                        f"{info.body[:500] if info.body else ''}"
                    ),
                    actions=[
                        ft.TextButton("Позже", on_click=lambda _: self.page.close(dlg)),
                        ft.ElevatedButton("Скачать", on_click=lambda _: self._do_update(info, dlg)),
                    ],
                )
                self.page.open(dlg)
            elif info:
                self._update_status_text.value = f"Новая версия: {info.version}"
                self._update_status_text.color = ft.colors.GREEN
                self.page.update()
            else:
                self._update_status_text.value = "У вас актуальная версия"
                self._update_status_text.color = ft.colors.GREY_700
                self.page.update()

        def _bg():
            try:
                info = check_latest(beta=self.beta_updates_switch.value)
                _done(info)
            except Exception:
                _done(None)

        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def _do_update(self, info, dlg):
        """Скачивает и применяет обновление."""
        import os
        import tempfile
        import threading

        from src.core.updater import apply_update, download_update

        self.page.close(dlg)
        self._update_status_text.value = "Скачивание..."
        self._check_update_btn.disabled = True
        self.page.update()

        def _dl():
            try:
                dest = os.path.join(tempfile.gettempdir(), f"NurBooks_{info.version}.exe")
                download_update(info.download_url, dest)
                self._update_status_text.value = "Скачано! Запуск..."
                self.page.update()
                apply_update(dest)
            except Exception as ex:
                self._update_status_text.value = f"Ошибка: {ex}"
                self.page.update()

        threading.Thread(target=_dl, daemon=True).start()

    def _get_downloaded_size(self) -> str:
        """Получает размер скачанных файлов"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk("downloads"):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(filepath)

            if total_size < 1024:
                return f"{total_size} B"
            elif total_size < 1024 * 1024:
                return f"{total_size / 1024:.1f} KB"
            else:
                return f"{total_size / (1024 * 1024):.1f} MB"
        except Exception:
            return "Неизвестно"

    def _on_theme_change(self, e):
        """Обработчик изменения темы"""
        theme = self.theme_dropdown.value or "light"

        # Применяем тему немедленно
        if theme == "dark":
            self.page.theme_mode = ft.ThemeMode.DARK
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.update()

    def _on_select_folder(self, e):
        """Обработчик выбора папки"""
        def on_folder_selected(e: ft.FilePickerResultEvent):
            if e.path:
                self.download_path_field.value = e.path
                self.page.update()

        file_picker = ft.FilePicker(on_result=on_folder_selected)
        self.page.overlay.append(file_picker)
        self.page.update()
        file_picker.get_directory_path()

    def _on_clear_cache(self, e):
        """Обработчик очистки кэша"""
        dlg = ft.AlertDialog(
            title=ft.Text("Очистка кэша"),
            content=ft.Text("Вы уверены, что хотите очистить кэш обложек?"),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda _: self.page.close(dlg),
                ),
                ft.TextButton("Очистить", on_click=lambda e: self._confirm_clear_cache(e, dlg)),
            ],
        )
        self.page.open(dlg)

    def _confirm_clear_cache(self, e, dlg):
        """Подтверждение очистки кэша"""
        try:
            import shutil

            if os.path.exists("data/thumbnails"):
                shutil.rmtree("data/thumbnails")
                os.makedirs("data/thumbnails")

            self.page.close(dlg)

            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Кэш очищен",
                    message="Кэш обложек успешно очищен",
                    type="success",
                )
        except Exception as ex:
            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Ошибка",
                    message=f"Не удалось очистить кэш: {ex}",
                    type="error",
                )

    def _on_show_folder(self, e):
        """Показать папку со скачанными файлами"""
        try:
            download_path = self.settings.default_path
            os.startfile(download_path) if os.name == "nt" else os.system(
                f'xdg-open "{download_path}"'
            )
        except Exception:
            pass

    def _on_export_data(self, e):
        """Экспорт данных пользователя в JSON-файл."""
        picker = ft.FilePicker(on_result=self._on_export_picked)
        self.page.overlay.append(picker)
        self.page.update()
        picker.save_file(
            dialog_title="Экспорт данных NurBooks",
            file_name="nurbooks_export.json",
            allowed_extensions=["json"],
        )

    def _on_export_picked(self, e: ft.FilePickerResultEvent):
        """Сохраняет собранные данные в выбранный файл."""
        path = e.path
        if not path:
            return
        try:
            import json
            from datetime import datetime

            from src.core.database import Database
            from src.core.favorites import favorites
            from src.core.wishlist import wishlist

            db = Database()
            data = {
                "app": "NurBooks",
                "exportedAt": datetime.now().isoformat(),
                "favorites": favorites.get_favorites(),
                "wishlist": wishlist.get_wishlist(),
                "readingHistory": db.get_reading_history(),
                "bookmarks": [
                    {"book_id": bm.book_id, "page": bm.page_number, "timestamp": bm.timestamp}
                    for bm, _ in db.get_all_bookmarks_with_books()
                ],
                "readingProgress": db.get_all_reading_progress(),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Экспорт завершён",
                    message=f"Данные сохранены в {path}",
                    type="success",
                )
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Данные экспортированы!"), action="OK")
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Ошибка экспорта: {ex}"),
                bgcolor=ft.colors.ERROR,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def _on_save_settings(self, e):
        """Сохранить настройки"""
        try:
            path_value = self.download_path_field.value or "downloads"
            # Нормализуем путь: если это дефолтная папка, сохраняем как "downloads"
            if path_value == NURBOOKS_DOWNLOADS_PATH:
                self.settings.default_path = "downloads"
            else:
                self.settings.default_path = path_value
            # Проверяем, что значение не None, иначе используем значение по умолчанию
            self.settings.theme = self.theme_dropdown.value or "light"
            self.settings.language = self.language_dropdown.value or "ru"
            self.settings.pdf_reader = self.pdf_reader_dropdown.value or "ask"
            # Сохраняем настройки уведомлений
            self.settings.download_notifications = self.download_notifications_switch.value
            self.settings.sound_notifications = self.sound_notifications_switch.value if self.sound_notifications_switch.value is not None else False
            self.settings.update_notifications = self.update_notifications_switch.value
            self.settings.background_notifications = self.background_notifications_switch.value if self.background_notifications_switch.value is not None else True
            self.settings.auto_update = self.auto_update_switch.value
            self.settings.beta_updates = self.beta_updates_switch.value

            self.storage.save_settings(self.settings)
            if self.notification_manager and hasattr(self.notification_manager, "set_sound_enabled"):
                self.notification_manager.set_sound_enabled(bool(self.settings.sound_notifications))
            if self.notification_manager and hasattr(self.notification_manager, "set_enabled"):
                self.notification_manager.set_enabled(bool(self.settings.background_notifications))

            # Применяем тему
            if self.settings.theme == "dark":
                self.page.theme_mode = ft.ThemeMode.DARK
            else:
                self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.update()

            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Настройки сохранены",
                    message="Настройки успешно сохранены",
                    type="success",
                )

            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Настройки успешно сохранены!"), action="OK"
            )
            self.page.snack_bar.open = True
            self.page.update()

        except Exception as ex:
            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Ошибка",
                    message=f"Не удалось сохранить настройки: {ex}",
                    type="error",
                )

    def _on_reset_settings(self, e):
        """Сбросить настройки"""
        dlg = ft.AlertDialog(
            title=ft.Text("Сброс настроек"),
            content=ft.Text(
                "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?"
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda _: self.page.close(dlg),
                ),
                ft.TextButton("Сбросить", on_click=lambda e: self._confirm_reset_settings(e, dlg)),
            ],
        )
        self.page.open(dlg)

    def _confirm_reset_settings(self, e, dlg):
        """Подтверждение сброса настроек"""
        try:
            self.settings = UserSettings(default_path="downloads")
            self.storage.save_settings(self.settings)

            self.download_path_field.value = NURBOOKS_DOWNLOADS_PATH
            self.theme_dropdown.value = self.settings.theme or "light"
            self.language_dropdown.value = self.settings.language or "ru"
            self.pdf_reader_dropdown.value = self.settings.pdf_reader or "ask"
            self.download_notifications_switch.value = self.settings.download_notifications
            self.sound_notifications_switch.value = self.settings.sound_notifications
            self.update_notifications_switch.value = self.settings.update_notifications
            self.background_notifications_switch.value = self.settings.background_notifications

            self.page.theme_mode = ft.ThemeMode.LIGHT

            self.page.close(dlg)

            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Настройки сброшены",
                    message="Настройки сброшены к значениям по умолчанию",
                    type="info",
                )

        except Exception as ex:
            if self.notification_manager:
                self.notification_manager.add_notification(
                    title="Ошибка",
                    message=f"Не удалось сбросить настройки: {ex}",
                    type="error",
                )

    def _update_account_section(self):
        """Обновляет блок аккаунта по текущему пользователю."""
        from src.core.firebase_client import firebase_client
        user = firebase_client.get_current_user()
        if user:
            label = user.get("nickname") or user.get("email") or "Анонимный пользователь"
            self._account_status_text.value = f"Вы вошли как: {label}"
            self._account_status_text.color = ft.colors.ON_SURFACE_VARIANT
            self._login_btn.visible = False
            self._logout_btn.visible = True
            self._register_btn.visible = False
        else:
            self._account_status_text.value = "Вход не выполнен. Без входа избранное и история общие для всех."
            self._account_status_text.color = ft.colors.GREY_700
            self._login_btn.visible = True
            self._logout_btn.visible = False
            self._register_btn.visible = True

    def _show_login_dialog(self, e=None):
        """Показывает диалог входа по email/паролю."""
        self._email_field.value = ""
        self._password_field.value = ""
        self._login_status_text.value = ""
        self._login_progress.visible = False
        dlg = ft.AlertDialog(
            title=ft.Text("Вход в аккаунт"),
            content=ft.Column(
                [
                    ft.Text("Войдите, чтобы синхронизировать избранное и историю чтения.", size=12, color=ft.colors.GREY_700),
                    self._email_field,
                    self._password_field,
                    ft.Row([self._login_progress, self._login_status_text], spacing=8),
                ],
                tight=True,
                spacing=12,
                width=320,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.close(dlg)),
                ft.ElevatedButton("Войти", icon=ft.icons.LOGIN, on_click=lambda _: self._on_login_submit(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._active_login_dlg = dlg
        self.page.open(dlg)

    def _on_login_submit(self, e=None, dlg=None):
        """Выполняет вход по email/паролю."""
        dlg = dlg or getattr(self, "_active_login_dlg", None)
        email = (self._email_field.value or "").strip()
        password = self._password_field.value or ""

        if not email or not password:
            self._login_status_text.value = "Введите email и пароль"
            self._login_status_text.color = ft.colors.ERROR
            self.page.update()
            return

        self._login_progress.visible = True
        self._login_status_text.value = "Вход..."
        self._login_status_text.color = ft.colors.GREY_700
        self.page.update()

        def _do():
            from src.core.favorites import favorites
            from src.core.firebase_client import firebase_client
            if "@" in email:
                uid = firebase_client.sign_in_with_email(email, password)
            else:
                uid = firebase_client.sign_in_with_nickname(email, password)
            if uid:
                favorites.load()
            self._login_progress.visible = False
            if uid:
                self._login_status_text.value = "Успешный вход!"
                self._login_status_text.color = ft.colors.GREEN
                self._update_account_section()
                if dlg:
                    self.page.close(dlg)
                if self.notification_manager:
                    self.notification_manager.add_notification(
                        title="Вход выполнен",
                        message=f"Вы вошли как: {email}",
                        type="success",
                    )
            else:
                self._login_status_text.value = "Не удалось войти. Проверьте email и пароль."
                self._login_status_text.color = ft.colors.ERROR
            self.page.update()

        import threading
        threading.Thread(target=_do, daemon=True).start()

    def _show_register_dialog(self, e=None):
        """Показывает диалог регистрации по нику и паролю."""
        self._register_nickname_field.value = ""
        self._register_password_field.value = ""
        self._register_status_text.value = ""
        self._register_progress.visible = False
        dlg = ft.AlertDialog(
            title=ft.Text("Регистрация"),
            content=ft.Column(
                [
                    ft.Text(
                        "Создайте аккаунт, чтобы синхронизировать избранное и историю чтения.",
                        size=12, color=ft.colors.GREY_700,
                    ),
                    self._register_nickname_field,
                    self._register_password_field,
                    ft.Row([self._register_progress, self._register_status_text], spacing=8),
                ],
                tight=True,
                spacing=12,
                width=320,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.close(dlg)),
                ft.ElevatedButton(
                    "Зарегистрироваться", icon=ft.icons.APP_REGISTRATION,
                    on_click=lambda _: self._on_register_submit(dlg),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._active_register_dlg = dlg
        self.page.open(dlg)

    def _on_register_submit(self, e=None, dlg=None):
        """Выполняет регистрацию по нику и паролю."""
        dlg = dlg or getattr(self, "_active_register_dlg", None)
        nickname = (self._register_nickname_field.value or "").strip()
        password = self._register_password_field.value or ""

        if not nickname or not password:
            self._register_status_text.value = "Введите ник и пароль"
            self._register_status_text.color = ft.colors.ERROR
            self.page.update()
            return
        if len(password) < 6:
            self._register_status_text.value = "Пароль должен быть не короче 6 символов"
            self._register_status_text.color = ft.colors.ERROR
            self.page.update()
            return

        self._register_progress.visible = True
        self._register_status_text.value = "Регистрация..."
        self._register_status_text.color = ft.colors.GREY_700
        self.page.update()

        def _do():
            from src.core.firebase_client import firebase_client
            uid = firebase_client.register_with_nickname(nickname, password)
            self._register_progress.visible = False
            if uid:
                self._register_status_text.value = "Аккаунт создан!"
                self._register_status_text.color = ft.colors.GREEN
                self._update_account_section()
                if dlg:
                    self.page.close(dlg)
                if self.notification_manager:
                    self.notification_manager.add_notification(
                        title="Регистрация успешна",
                        message=f"Вы зарегистрированы как: {nickname}",
                        type="success",
                    )
            else:
                self._register_status_text.value = "Не удалось создать аккаунт. Возможно, ник уже занят."
                self._register_status_text.color = ft.colors.ERROR
            self.page.update()

        import threading
        threading.Thread(target=_do, daemon=True).start()

    def _on_logout(self, e=None):
        """Выход из аккаунта."""
        from src.core.favorites import favorites
        from src.core.firebase_client import firebase_client
        firebase_client.sign_out()
        favorites.load()
        self._update_account_section()
        self.page.update()
        if self.notification_manager:
            self.notification_manager.add_notification(
                title="Выход выполнен",
                message="Вы вышли из аккаунта",
                type="info",
            )

    def _close_dialog(self, e=None, dlg=None):
        """Закрыть диалог"""
        if dlg:
            self.page.close(dlg)

    def build(self) -> ft.Control:
        """Возвращает содержимое страницы"""
        return self.content
