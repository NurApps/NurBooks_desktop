import json
import os
from collections.abc import Callable
from datetime import datetime

from src.core.models import Notification


class NotificationManager:
    def __init__(self, storage_path: str = "data/notifications.json", sound_enabled: bool = True, enabled: bool = True):
        self.storage_path = storage_path
        self.notifications: list[Notification] = []
        self.next_id = 1
        self._unread_count = 0
        self._on_update_callbacks: list[Callable] = []
        self.sound_enabled = sound_enabled
        self.enabled = enabled

        # Загружаем сохраненные уведомления
        self._load_notifications()

    def _load_notifications(self):
        """Загружает уведомления из файла"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, encoding='utf-8') as f:
                    data = json.load(f)
                    self.next_id = data.get('next_id', 1)
                    self._unread_count = data.get('unread_count', 0)

                    for item in data.get('notifications', []):
                        try:
                            timestamp = datetime.fromisoformat(item['timestamp'])
                            notification = Notification(
                                id=item['id'],
                                title=item['title'],
                                message=item['message'],
                                type=item['type'],
                                timestamp=timestamp
                            )
                            self.notifications.append(notification)
                        except (KeyError, ValueError):
                            continue
        except Exception as e:
            print(f"Ошибка загрузки уведомлений: {e}")
            self.notifications = []
            self.next_id = 1
            self._unread_count = 0

    def _save_notifications(self):
        """Сохраняет уведомления в файл"""
        try:
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

            data = {
                'next_id': self.next_id,
                'unread_count': self._unread_count,
                'notifications': [n.to_dict() for n in self.notifications]
            }

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"Ошибка сохранения уведомлений: {e}")

    def add_update_callback(self, callback: Callable):
        """Добавляет callback для обновления UI"""
        if callback not in self._on_update_callbacks:
            self._on_update_callbacks.append(callback)

    def remove_update_callback(self, callback: Callable):
        """Удаляет callback"""
        if callback in self._on_update_callbacks:
            self._on_update_callbacks.remove(callback)

    def _notify_update(self):
        """Уведомляет все зарегистрированные callback'и"""
        for callback in self._on_update_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Ошибка в callback уведомлений: {e}")

    def add_notification(self, title: str, message: str, type: str = "info"):
        """Добавить новое уведомление"""
        if not self.enabled:
            return None
        notification = Notification(
            id=self.next_id,
            title=title,
            message=message,
            type=type,
            timestamp=datetime.now()
        )
        self.notifications.insert(0, notification)  # Новые уведомления в начале
        self.next_id += 1
        self._unread_count += 1

        # Ограничиваем количество уведомлений
        if len(self.notifications) > 100:
            self.notifications = self.notifications[:100]

        self._save_notifications()
        self._notify_update()
        self._play_sound(type)

        return notification

    def set_sound_enabled(self, enabled: bool):
        self.sound_enabled = bool(enabled)

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled)

    def _play_sound(self, notification_type: str):
        if not self.sound_enabled:
            return
        try:
            if os.name == "nt":
                import winsound
                if notification_type == "error":
                    winsound.MessageBeep(winsound.MB_ICONHAND)
                elif notification_type == "warning":
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                else:
                    winsound.MessageBeep(winsound.MB_OK)
            else:
                print("\a", end="")
        except Exception:
            pass

    def get_notifications(self) -> list[Notification]:
        """Получить все уведомления"""
        return self.notifications

    def get_unread_count(self) -> int:
        """Получить количество непрочитанных уведомлений"""
        return self._unread_count

    def mark_as_read(self):
        """Отметить все уведомления как прочитанные"""
        self._unread_count = 0
        self._save_notifications()
        self._notify_update()

    def clear_notifications(self):
        """Очистить все уведомления"""
        self.notifications.clear()
        self._unread_count = 0
        self._save_notifications()
        self._notify_update()

    def remove_notification(self, notification_id: int):
        """Удалить конкретное уведомление"""
        self.notifications = [n for n in self.notifications if n.id != notification_id]
        if self._unread_count > 0:
            self._unread_count -= 1
        self._save_notifications()
        self._notify_update()

    # Предустановленные типы уведомлений
    def notify_book_downloaded(self, book_title: str, file_size: str = ""):
        """Уведомление о скачивании книги"""
        message = f"Книга '{book_title}' успешно скачана"
        if file_size:
            message += f" ({file_size})"
        return self.add_notification(
            title="Книга скачана",
            message=message,
            type="success"
        )

    def notify_book_deleted(self, book_title: str):
        """Уведомление об удалении книги"""
        return self.add_notification(
            title="Книга удалена",
            message=f"Книга '{book_title}' была удалена",
            type="warning"
        )

    def notify_book_added_to_cart(self, book_title: str):
        """Уведомление о добавлении в корзину"""
        return self.add_notification(
            title="Добавлено в корзину",
            message=f"Книга '{book_title}' добавлена в корзину",
            type="info"
        )

    def notify_book_removed_from_cart(self, book_title: str):
        """Уведомление об удалении из корзины"""
        return self.add_notification(
            title="Удалено из корзины",
            message=f"Книга '{book_title}' удалена из корзины",
            type="info"
        )

    def notify_book_added_to_library(self, book_title: str):
        """Уведомление о добавлении в библиотеку"""
        return self.add_notification(
            title="Книга сохранена",
            message=f"Книга '{book_title}' добавлена в вашу библиотеку",
            type="success"
        )

    def notify_error(self, title: str, message: str):
        """Уведомление об ошибке"""
        return self.add_notification(
            title=title,
            message=message,
            type="error"
        )

    def notify_success(self, title: str, message: str):
        """Уведомление об успехе"""
        return self.add_notification(
            title=title,
            message=message,
            type="success"
        )

    def notify_info(self, title: str, message: str):
        """Информационное уведомление"""
        return self.add_notification(
            title=title,
            message=message,
            type="info"
        )
