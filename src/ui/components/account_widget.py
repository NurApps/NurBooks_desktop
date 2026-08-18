"""
Виджет аккаунта в верхней панели: быстрый вход, регистрация и выход.

Показывает текущего пользователя (ник или «Войти»), по клику открывает
меню с действиями. Логика дублирует блок «Аккаунт» в настройках, но
работает из любой страницы приложения.
"""
import threading

import flet as ft

from src.core.notifications import NotificationManager


class AccountWidget:
    def __init__(self, page: ft.Page, notification_manager: NotificationManager | None = None,
                 on_change=None):
        self.page = page
        self.notification_manager = notification_manager
        self.on_change = on_change

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

        self._active_login_dlg: ft.AlertDialog | None = None
        self._active_register_dlg: ft.AlertDialog | None = None

    # ---------- Публичное ----------

    def build(self) -> ft.Control:
        """Возвращает кнопку-аватар с меню аккаунта."""
        return self._build_button()

    def set_mobile(self, mobile: bool):
        """На мобильном показывает только аватар без подписи."""
        self._mobile = mobile
        if hasattr(self, "_button"):
            self._button = self._build_button()
        return self._button

    def refresh(self):
        """Перестраивает кнопку под текущего пользователя."""
        self._button = self._build_button()
        return self._button

    # ---------- Построение ----------

    def _build_button(self) -> ft.PopupMenuButton:
        user = self._current_user()
        if user:
            label = user.get("nickname") or user.get("email") or "Аккаунт"
            avatar = ft.CircleAvatar(
                radius=18,
                content=ft.Text(label[:1].upper(), weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
                bgcolor=ft.colors.PRIMARY,
            )
            menu_items = [
                ft.PopupMenuItem(
                    text=f"Вы вошли как: {label}",
                    disabled=True,
                ),
                ft.PopupMenuItem(divider=True),
                ft.PopupMenuItem(
                    text="Выйти",
                    icon=ft.icons.LOGOUT,
                    on_click=self._on_logout,
                ),
            ]
        else:
            avatar = ft.CircleAvatar(
                radius=18,
                content=ft.Icon(ft.icons.PERSON, color=ft.colors.WHITE),
                bgcolor=ft.colors.OUTLINE,
            )
            menu_items = [
                ft.PopupMenuItem(
                    text="Войти",
                    icon=ft.icons.LOGIN,
                    on_click=self._on_login_click,
                ),
                ft.PopupMenuItem(
                    text="Регистрация",
                    icon=ft.icons.APP_REGISTRATION,
                    on_click=self._on_register_click,
                ),
            ]

        self._mobile = getattr(self, "_mobile", False)

        return ft.PopupMenuButton(
            content=ft.Row([
                avatar,
                ft.Text(
                    label[:12] + ("..." if len(label) > 12 else "") if user else "Войти",
                    size=13,
                    weight=ft.FontWeight.BOLD if user else ft.FontWeight.NORMAL,
                    color=ft.colors.PRIMARY if user else ft.colors.ON_SURFACE_VARIANT,
                    visible=not self._mobile,
                ),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            items=menu_items,
            tooltip="Аккаунт",
        )

    def _current_user(self) -> dict | None:
        try:
            from src.core.firebase_client import firebase_client
            if not firebase_client.is_initialized():
                return None
            return firebase_client.get_current_user()
        except Exception:
            return None

    # ---------- Вход ----------

    def _on_login_click(self, e=None):
        self._email_field.value = ""
        self._password_field.value = ""
        self._login_status_text.value = ""
        self._login_progress.visible = False
        dlg = ft.AlertDialog(
            title=ft.Text("Вход в аккаунт"),
            content=ft.Column(
                [
                    ft.Text("Войдите, чтобы синхронизировать избранное и историю чтения.",
                            size=12, color=ft.colors.GREY_700),
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
        self.page.update()

    def _on_login_submit(self, e=None, dlg=None):
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
                if dlg:
                    self.page.close(dlg)
                self._notify("Вход выполнен", f"Вы вошли как: {email}", "success")
                self._after_change()
            else:
                self._login_status_text.value = "Не удалось войти. Проверьте email и пароль."
                self._login_status_text.color = ft.colors.ERROR
            self.page.update()

        threading.Thread(target=_do, daemon=True).start()

    # ---------- Регистрация ----------

    def _on_register_click(self, e=None):
        self._register_nickname_field.value = ""
        self._register_password_field.value = ""
        self._register_status_text.value = ""
        self._register_progress.visible = False
        dlg = ft.AlertDialog(
            title=ft.Text("Регистрация"),
            content=ft.Column(
                [
                    ft.Text("Создайте аккаунт, чтобы синхронизировать избранное и историю чтения.",
                            size=12, color=ft.colors.GREY_700),
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
        self.page.update()

    def _on_register_submit(self, e=None, dlg=None):
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
                if dlg:
                    self.page.close(dlg)
                self._notify("Регистрация успешна", f"Вы зарегистрированы как: {nickname}", "success")
                self._after_change()
            else:
                self._register_status_text.value = "Не удалось создать аккаунт. Возможно, ник уже занят."
                self._register_status_text.color = ft.colors.ERROR
            self.page.update()

        threading.Thread(target=_do, daemon=True).start()

    # ---------- Выход ----------

    def _on_logout(self, e=None):
        from src.core.favorites import favorites
        from src.core.firebase_client import firebase_client
        firebase_client.sign_out()
        favorites.load()
        self._notify("Выход выполнен", "Вы вышли из аккаунта", "info")
        self._after_change()

    # ---------- Вспомогательное ----------

    def _notify(self, title, message, kind="info"):
        if self.notification_manager:
            self.notification_manager.add_notification(title=title, message=message, type=kind)

    def _after_change(self):
        self.refresh()
        if self.on_change:
            self.on_change()
        self.page.update()
