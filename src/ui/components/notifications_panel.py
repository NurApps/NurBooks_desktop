from collections.abc import Callable
from datetime import datetime

import flet as ft

from src.core.models import Notification


class NotificationDetailDialog:
    """Диалоговое окно для детального просмотра уведомления"""

    def __init__(self, notification: Notification, on_close: Callable = None, on_delete: Callable = None):
        self.notification = notification
        self.on_close = on_close
        self.on_delete = on_delete
        self.dialog = None

    def _get_icon_for_type(self, type: str) -> str:
        """Получить иконку для типа уведомления"""
        icons = {
            "success": ft.icons.CHECK_CIRCLE_ROUNDED,
            "error": ft.icons.ERROR_ROUNDED,
            "warning": ft.icons.WARNING_ROUNDED,
            "info": ft.icons.INFO_ROUNDED
        }
        return icons.get(type, ft.icons.INFO_ROUNDED)

    def _get_color_for_type(self, type: str) -> str:
        """Получить цвет для типа уведомления"""
        colors = {
            "success": ft.colors.GREEN,
            "error": ft.colors.RED,
            "warning": ft.colors.ORANGE,
            "info": ft.colors.BLUE
        }
        return colors.get(type, ft.colors.BLUE)

    def _get_type_label(self, type: str) -> str:
        """Получить текстовое название типа уведомления"""
        types = {
            "success": "Успех",
            "error": "Ошибка",
            "warning": "Предупреждение",
            "info": "Информация"
        }
        return types.get(type, "Информация")

    def _format_full_datetime(self, timestamp: datetime) -> str:
        """Форматирование полной даты и времени"""
        # Полная дата
        date_str = timestamp.strftime("%d.%m.%Y")
        # Время
        time_str = timestamp.strftime("%H:%M:%S")
        # День недели
        weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        weekday = weekdays[timestamp.weekday()]

        return f"{date_str}, {time_str}\n{weekday}"

    def _format_relative_time(self, timestamp: datetime) -> str:
        """Форматирование относительного времени"""
        now = datetime.now()
        diff = now - timestamp

        if diff.days > 365:
            return timestamp.strftime("%d.%m.%Y")
        elif diff.days > 0:
            return timestamp.strftime("%d.%m %H:%M")
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} ч. назад"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} мин. назад"
        else:
            return "только что"

    def build(self) -> ft.AlertDialog:
        """Создает диалоговое окно"""
        icon_color = self._get_color_for_type(self.notification.type)

        return ft.AlertDialog(
            title=ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(
                            self._get_icon_for_type(self.notification.type),
                            color=icon_color,
                            size=28,
                        ),
                        bgcolor=ft.colors.SURFACE_VARIANT,
                        border_radius=20,
                        width=40,
                        height=40,
                        alignment=ft.alignment.center,
                    ),
                    ft.Text(
                        "Детали уведомления",
                        weight=ft.FontWeight.BOLD,
                        size=18,
                    ),
                ]),
                padding=10,
            ),
            content=ft.Container(
                content=ft.Column([
                    # Заголовок
                    ft.Container(
                        content=ft.Text(
                            self.notification.title,
                            weight=ft.FontWeight.BOLD,
                            size=16,
                        ),
                        padding=ft.padding.only(bottom=10),
                    ),

                    # Сообщение
                    ft.Container(
                        content=ft.Text(
                            self.notification.message,
                            size=14,
                            color=ft.colors.ON_SURFACE_VARIANT,
                        ),
                        padding=ft.padding.only(bottom=15),
                    ),

                    ft.Divider(),

                    # Информация о времени
                    ft.Column([
                        # Тип уведомления
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.CATEGORY_ROUNDED, size=16, color=ft.colors.OUTLINE),
                                ft.Text("Тип:", size=12, color=ft.colors.OUTLINE),
                                ft.Container(expand=True),
                                ft.Container(
                                    content=ft.Row([
                                        ft.Icon(self._get_icon_for_type(self.notification.type), size=14, color=icon_color),
                                        ft.Text(self._get_type_label(self.notification.type), size=12, weight=ft.FontWeight.W_500),
                                    ], spacing=4),
                                    bgcolor=ft.colors.SURFACE_VARIANT,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                    border_radius=12,
                                ),
                            ]),
                            padding=ft.padding.only(bottom=8),
                        ),

                        # Относительное время
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.SCHEDULE_ROUNDED, size=16, color=ft.colors.OUTLINE),
                                ft.Text("Время:", size=12, color=ft.colors.OUTLINE),
                                ft.Container(expand=True),
                                ft.Text(self._format_relative_time(self.notification.timestamp), size=12, weight=ft.FontWeight.W_500),
                            ]),
                            padding=ft.padding.only(bottom=8),
                        ),

                        # Полная дата и время
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.CALENDAR_TODAY_ROUNDED, size=16, color=ft.colors.OUTLINE),
                                ft.Text("Дата:", size=12, color=ft.colors.OUTLINE),
                                ft.Container(expand=True),
                                ft.Text(self._format_full_datetime(self.notification.timestamp), size=12, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.RIGHT),
                            ]),
                            padding=ft.padding.only(bottom=8),
                        ),

                        # ID уведомления
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.NUMBERS_ROUNDED, size=16, color=ft.colors.OUTLINE),
                                ft.Text("ID:", size=12, color=ft.colors.OUTLINE),
                                ft.Container(expand=True),
                                ft.Text(f"#{self.notification.id}", size=12, color=ft.colors.OUTLINE),
                            ]),
                        ),
                    ], spacing=0),
                ], spacing=5),
                padding=10,
                width=400,
            ),
            actions=[
                ft.TextButton(
                    "Удалить",
                    icon=ft.icons.DELETE_ROUNDED,
                    on_click=self._on_delete_click,
                    style=ft.ButtonStyle(color=ft.colors.RED),
                ),
                ft.TextButton(
                    "Закрыть",
                    on_click=self._on_close_click,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _on_close_click(self, e):
        if self.on_close:
            self.on_close()

    def _on_delete_click(self, e):
        if self.on_delete:
            self.on_delete(self.notification.id)


class NotificationsPanel:
    """Панель уведомлений с красивым дизайном"""

    def __init__(self, on_clear_all: Callable | None = None, on_notification_click: Callable | None = None, on_notification_detail: Callable | None = None):
        self.on_clear_all = on_clear_all
        self.on_notification_click = on_notification_click
        self.on_notification_detail = on_notification_detail
        self.notifications: list[Notification] = []
        self.unread_count = 0

    def set_notifications(self, notifications: list[Notification], unread_count: int = 0):
        """Установить список уведомлений"""
        self.notifications = notifications
        self.unread_count = unread_count

    def _get_icon_for_type(self, type: str) -> str:
        """Получить иконку для типа уведомления"""
        icons = {
            "success": ft.icons.CHECK_CIRCLE_ROUNDED,
            "error": ft.icons.ERROR_ROUNDED,
            "warning": ft.icons.WARNING_ROUNDED,
            "info": ft.icons.INFO_ROUNDED
        }
        return icons.get(type, ft.icons.INFO_ROUNDED)

    def _get_color_for_type(self, type: str) -> str:
        """Получить цвет для типа уведомления"""
        colors = {
            "success": ft.colors.GREEN,
            "error": ft.colors.RED,
            "warning": ft.colors.ORANGE,
            "info": ft.colors.BLUE
        }
        return colors.get(type, ft.colors.BLUE)

    def _get_bgcolor_for_type(self, type: str) -> str:
        """Получить фоновый цвет для типа уведомления"""
        colors = {
            "success": ft.colors.GREEN_50,
            "error": ft.colors.RED_50,
            "warning": ft.colors.ORANGE_50,
            "info": ft.colors.BLUE_50
        }
        return colors.get(type, ft.colors.BLUE_50)

    def _format_time(self, timestamp: datetime) -> str:
        """Форматирование времени для отображения"""
        now = datetime.now()
        diff = now - timestamp

        if diff.days > 365:
            return timestamp.strftime("%d.%m.%Y")
        elif diff.days > 0:
            return timestamp.strftime("%d.%m %H:%M")
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} ч. назад"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} мин. назад"
        else:
            return "только что"

    def _create_notification_item(self, notification: Notification) -> ft.Control:
        """Создает элемент уведомления"""
        icon_color = self._get_color_for_type(notification.type)
        bg_color = self._get_bgcolor_for_type(notification.type)

        # Обработчик клика для детального просмотра
        def on_detail_click(e):
            if self.on_notification_detail:
                self.on_notification_detail(notification)

        return ft.Container(
            content=ft.Row(
                [
                    # Иконка
                    ft.Container(
                        content=ft.Icon(
                            self._get_icon_for_type(notification.type),
                            color=icon_color,
                            size=22,
                        ),
                        bgcolor=bg_color,
                        border_radius=20,
                        width=40,
                        height=40,
                        alignment=ft.alignment.center,
                    ),

                    # Текст
                    ft.Column(
                        [
                            ft.Text(
                                notification.title,
                                weight=ft.FontWeight.W_600,
                                size=14,
                                color=ft.colors.ON_SURFACE,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS
                            ),
                            ft.Text(
                                notification.message,
                                size=12,
                                color=ft.colors.ON_SURFACE_VARIANT,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS
                            ),
                            ft.Text(
                                self._format_time(notification.timestamp),
                                size=10,
                                color=ft.colors.OUTLINE,
                            ),
                        ],
                        expand=True,
                        spacing=2,
                    ),

                    # Кнопка информации и закрытия
                    ft.Column(
                        [
                            ft.IconButton(
                                icon=ft.icons.INFO_ROUNDED,
                                icon_size=16,
                                icon_color=ft.colors.OUTLINE,
                                tooltip="Подробнее",
                                on_click=on_detail_click,
                                style=ft.ButtonStyle(
                                    bgcolor=ft.colors.TRANSPARENT,
                                ),
                            ),
                            ft.IconButton(
                                icon=ft.icons.CLOSE_ROUNDED,
                                icon_size=16,
                                icon_color=ft.colors.OUTLINE,
                                style=ft.ButtonStyle(
                                    bgcolor=ft.colors.TRANSPARENT,
                                ),
                                on_click=lambda e, nid=notification.id: self._on_notification_click(nid),
                            ),
                        ],
                        spacing=0,
                    ),
                ],
                spacing=12,
            ),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            bgcolor=ft.colors.SURFACE,
            border_radius=12,
            border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
            margin=ft.margin.only(bottom=8),
            animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_OUT),
        )

    def build(self) -> ft.Control:
        """Создает панель уведомлений"""
        if not self.notifications:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=40),
                        ft.Icon(
                            ft.icons.NOTIFICATIONS_NONE_ROUNDED,
                            size=64,
                            color=ft.colors.OUTLINE
                        ),
                        ft.Text(
                            "Нет уведомлений",
                            size=18,
                            color=ft.colors.OUTLINE,
                            weight=ft.FontWeight.W_500
                        ),
                        ft.Text(
                            "Здесь будут отображаться уведомления",
                            size=12,
                            color=ft.colors.OUTLINE_VARIANT,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    expand=True,
                    spacing=12,
                ),
                expand=True,
            )

        notification_items = []
        for notification in self.notifications:
            notification_items.append(self._create_notification_item(notification))

        return ft.Column(
            controls=[
                ft.Text(
                    f"Всего: {len(self.notifications)}",
                    size=12,
                    color=ft.colors.ON_SURFACE_VARIANT,
                ),
                ft.Divider(height=1, color=ft.colors.OUTLINE_VARIANT),
                ft.Container(height=8),
                ft.Column(
                    controls=notification_items,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )

    def _on_notification_click(self, notification_id: int):
        if self.on_notification_click:
            self.on_notification_click(notification_id)


class NotificationBadge(ft.Container):
    """Бейдж с количеством непрочитанных уведомлений"""

    def __init__(self, count: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.count = count
        self._update_content()

    def _update_content(self):
        self.content = ft.Container(
            content=ft.Text(
                str(self.count) if self.count < 100 else "99+",
                size=10,
                color=ft.colors.WHITE,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
            ),
            bgcolor=ft.colors.RED,
            border_radius=10,
            width=20 if self.count < 10 else None,
            height=20,
            padding=ft.padding.symmetric(horizontal=4) if self.count >= 10 else None,
            alignment=ft.alignment.center,
            visible=self.count > 0,
            animate=ft.animation.Animation(200, ft.AnimationCurve.ELASTIC_OUT),
        )
        self.visible = self.count > 0

    def set_count(self, count: int):
        self.count = count
        self._update_content()


class NotificationButton(ft.Container):
    """Кнопка уведомлений с бейджем"""

    def __init__(
        self,
        on_click: Callable | None = None,
        count: int = 0,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._count = count
        self._on_click = on_click
        self._badge = None
        self._build()

    def _build(self):
        self._badge = NotificationBadge(count=self._count)

        self.content = ft.Stack(
            controls=[
                ft.IconButton(
                    icon=ft.icons.NOTIFICATIONS_ROUNDED,
                    tooltip="Уведомления",
                    on_click=self._on_click_handler,
                    icon_color=ft.colors.PRIMARY,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                ),
                ft.Container(
                    content=self._badge,
                    top=2,
                    right=2,
                ),
            ],
        )

    def _on_click_handler(self, e):
        if self._on_click:
            self._on_click(e)

    def set_count(self, count: int):
        self._count = count
        if self._badge:
            self._badge.set_count(count)
