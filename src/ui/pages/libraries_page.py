"""
Раздел «Библиотеки» — общие коллекции книг.

Пользователи создают библиотеки (публичные или приватные), добавляют книги,
делятся ими через инвайт-код. Другие могут смотреть и читать книги из библиотеки.
"""
import threading

import flet as ft

from src.core.notifications import NotificationManager
from src.core.storage import Storage


class LibrariesPage:
    def __init__(self, page: ft.Page, notification_manager: NotificationManager | None = None,
                 on_back=None, on_read_book=None):
        self.page = page
        self.notification_manager = notification_manager
        self.on_back = on_back
        self.on_read_book = on_read_book
        self.storage = Storage()
        self._libraries: list[dict] = []
        self._all_books = []
        self._current_lib: dict | None = None
        self._current_rating: dict = {}
        self._list_container = ft.Container(expand=True)
        self.content = self._create_content()
        self._load_all_books()
        self._refresh()

    # ---------- Вспомогательное ----------

    def _load_all_books(self):
        try:
            self._all_books = self.storage.load_books()
        except Exception:
            self._all_books = []

    def _find_book(self, book_id) -> dict | None:
        for b in self._all_books:
            if b.id == int(book_id):
                return b
        return None

    def _notify(self, title, message, kind="info"):
        if self.notification_manager:
            self.notification_manager.add_notification(title=title, message=message, type=kind)

    # ---------- Layout ----------

    def _create_content(self) -> ft.Control:
        self._create_btn = ft.ElevatedButton("Создать библиотеку", icon=ft.icons.ADD, on_click=self._show_create_dialog)
        self._join_btn = ft.OutlinedButton("Вступить по коду", icon=ft.icons.PERSON_ADD, on_click=self._show_join_dialog)
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=self._on_back, tooltip="Назад"),
                        ft.Text("Библиотеки", size=28, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        self._join_btn,
                        self._create_btn,
                    ]),
                    padding=ft.padding.only(left=20, right=20, top=20, bottom=10),
                ),
                ft.Divider(),
                self._list_container,
            ], spacing=0),
            expand=True,
        )

    def _on_back(self, e=None):
        if self._current_lib is not None:
            self._current_lib = None
            self._rebuild_list_view()
            return
        if self.on_back:
            self.on_back()

    # ---------- Список библиотек ----------

    def _refresh(self):
        threading.Thread(target=self._load_libraries, daemon=True).start()

    def _load_libraries(self):
        try:
            from src.core.firebase_client import firebase_client
            if not firebase_client.is_initialized():
                self._list_container.content = ft.Text("Сервер недоступен. Библиотеки требуют подключения.", size=14, color=ft.colors.GREY)
                self.page.update()
                return
            data = firebase_client.get_libraries()
            self._libraries = data or []
            for lib in self._libraries:
                try:
                    lib["rating"] = firebase_client.get_library_rating(lib.get("id")) or {}
                except Exception:
                    lib["rating"] = {}
            self._rebuild_list_view()
            self.page.update()
        except Exception as e:
            self._list_container.content = ft.Text(f"Ошибка загрузки: {e}", size=14, color=ft.colors.GREY)
            self.page.update()

    def _rebuild_list_view(self):
        if not self._libraries:
            self._list_container.content = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.LIBRARY_BOOKS, size=52, color=ft.colors.GREY),
                    ft.Text("Пока нет библиотек", size=18, color=ft.colors.GREY),
                    ft.Text("Создайте свою библиотеку или вступите по коду приглашения", size=13, color=ft.colors.GREY_600),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                alignment=ft.alignment.center,
                expand=True,
            )
            return

        items = [self._create_library_card(lib) for lib in self._libraries]
        self._list_container.content = ft.Container(
            content=ft.Column(items, scroll=ft.ScrollMode.ADAPTIVE),
            padding=20,
            expand=True,
        )

    def _create_library_card(self, lib: dict) -> ft.Control:
        visibility = "Публичная" if lib.get("visibility") == "public" else "Приватная"
        owner = lib.get("ownerNickname") or "Владелец"
        rating = lib.get("rating") or {}
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.icons.LIBRARY_BOOKS, color=ft.colors.PRIMARY, size=28),
                    bgcolor=ft.colors.PRIMARY_CONTAINER,
                    border_radius=12,
                    width=52,
                    height=52,
                    alignment=ft.alignment.center,
                ),
                ft.Column([
                    ft.Text(lib.get("title", "Библиотека"), weight=ft.FontWeight.BOLD, size=16),
                    ft.Text(
                        f"{owner} • {lib.get('bookCount', 0)} книг • {lib.get('memberCount', 0)} участников",
                        size=12, color=ft.colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Text(lib.get("description", ""), size=12, color=ft.colors.GREY,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS) if lib.get("description") else ft.Container(),
                    self._rating_line(rating) if rating else ft.Container(),
                ], expand=True, spacing=3),
                ft.Container(
                    content=ft.Text(visibility, size=11),
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                    bgcolor=ft.colors.SECONDARY_CONTAINER,
                    border_radius=12,
                ),
                ft.FilledTonalButton("Открыть", icon=ft.icons.OPEN_IN_NEW, on_click=lambda e, lid=lib.get("id"): self._open_library(lid)),
            ], spacing=14),
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            bgcolor=ft.colors.SURFACE,
            border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
            border_radius=12,
            margin=ft.margin.only(bottom=8),
        )

    # ---------- Просмотр библиотеки ----------

    def _open_library(self, lib_id: str):
        def _load():
            try:
                from src.core.firebase_client import firebase_client
                lib = firebase_client.get_library(lib_id)
                if lib is None:
                    self._notify("Ошибка", "Библиотека не найдена", "error")
                    return
                self._current_lib = lib
                self._load_rating(lib_id, lambda r: self._set_rating_loaded(lib_id, r))
                self._build_library_detail()
                self.page.update()
            except Exception as e:
                self._notify("Ошибка", f"Не удалось открыть библиотеку: {e}", "error")
        threading.Thread(target=_load, daemon=True).start()

    def _build_library_detail(self):
        lib = self._current_lib
        user = self._current_uid()

        books = [self._find_book(bid) for bid in lib.get("bookIds", [])]
        books = [b for b in books if b]

        is_owner = lib.get("ownerUid") == user

        book_cards = []
        for b in books:
            book_cards.append(self._create_library_book_card(b, is_owner))

        if not book_cards:
            empty = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.LIBRARY_ADD, size=48, color=ft.colors.GREY),
                    ft.Text("В библиотеке пока нет книг", size=15, color=ft.colors.GREY),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=30,
                alignment=ft.alignment.center,
            )
        else:
            empty = ft.Container()

        invite_row = ft.Row([
            ft.Text("Код приглашения:", size=13, color=ft.colors.GREY),
            ft.Text(lib.get("inviteCode", ""), weight=ft.FontWeight.BOLD, size=14, color=ft.colors.PRIMARY),
            ft.TextButton("Копировать", on_click=lambda e, code=lib.get("inviteCode", ""): self._copy_invite(code)),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        rating_block = self._build_rating_block(lib_id=lib.get("id"))

        actions = []
        if is_owner:
            actions.append(ft.ElevatedButton("Добавить книгу", icon=ft.icons.ADD, on_click=self._show_add_book_dialog))
            actions.append(ft.OutlinedButton("Удалить библиотеку", icon=ft.icons.DELETE, on_click=self._confirm_delete_library))

        self._list_container.content = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=self._on_back, tooltip="Назад к списку"),
                        ft.Column([
                            ft.Text(lib.get("title", "Библиотека"), size=22, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                f"{lib.get('ownerNickname', 'Владелец')} • {len(book_cards)} книг",
                                size=12, color=ft.colors.ON_SURFACE_VARIANT,
                            ),
                        ], spacing=2, expand=True),
                        *actions,
                    ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.only(left=16, right=20, top=16, bottom=6),
                ),
                ft.Divider(),
                ft.Container(
                    content=ft.Column([
                        invite_row,
                        rating_block,
                        *book_cards,
                        empty,
                    ], spacing=8),
                    padding=20,
                    expand=True,
                ),
            ], spacing=0),
            expand=True,
        )

    def _create_library_book_card(self, book, is_owner: bool) -> ft.Control:
        cover = getattr(book, "cover", "") or "assets/logo.png"
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Image(src=cover, width=36, height=48, fit=ft.ImageFit.COVER, border_radius=4),
                ),
                ft.Column([
                    ft.Text(book.title, weight=ft.FontWeight.BOLD, size=14, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(book.author, size=12, color=ft.colors.ON_SURFACE_VARIANT),
                ], expand=True, spacing=2),
                ft.FilledTonalButton("Читать", icon=ft.icons.MENU_BOOK, on_click=lambda e, b=book: self._read_book(b)),
                ft.IconButton(
                    icon=ft.icons.DELETE,
                    tooltip="Убрать из библиотеки",
                    visible=is_owner,
                    on_click=lambda e, lid=self._current_lib.get("id"), bid=book.id: self._remove_book(lid, bid),
                ),
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=12, vertical=10),
            bgcolor=ft.colors.SURFACE,
            border=ft.border.all(1, ft.colors.OUTLINE_VARIANT),
            border_radius=12,
            margin=ft.margin.only(bottom=6),
        )

    def _current_uid(self) -> str:
        try:
            from src.core.firebase_client import firebase_client
            user = firebase_client.get_current_user()
            return (user or {}).get("uid", "")
        except Exception:
            return ""

    # ---------- Рейтинг библиотеки ----------

    def _star_row(self, value: int, size: int = 22) -> ft.Row:
        return ft.Row(
            [ft.Icon(ft.icons.STAR_RATE if i <= value else ft.icons.STAR_BORDER,
                     color=ft.colors.AMBER if i <= value else ft.colors.OUTLINE, size=size)
             for i in range(1, 6)],
            spacing=2, tight=True,
        )

    def _rating_line(self, rating: dict) -> ft.Control:
        avg = rating.get("average") or 0
        count = rating.get("count") or 0
        if count == 0:
            return ft.Text("Ещё нет оценок", size=12, color=ft.colors.GREY)
        return ft.Row([
            self._star_row(round(avg)),
            ft.Text(f"{avg:.1f} ({count} {'оценка' if count % 10 == 1 and count % 100 != 11 else 'оценки' if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14) else 'оценок'})",
                    size=12, color=ft.colors.ON_SURFACE_VARIANT),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _build_rating_block(self, lib_id: str) -> ft.Control:
        rating = self._current_rating or {}
        my = rating.get("myRating")
        avg = rating.get("average") or 0
        count = rating.get("count") or 0

        stars = ft.Row(
            [ft.IconButton(
                icon=ft.icons.STAR_RATE if (my or 0) >= i else ft.icons.STAR_BORDER,
                icon_color=ft.colors.AMBER,
                icon_size=28,
                tooltip=f"{i}",
                on_click=lambda e, n=i: self._set_rating(lib_id, n),
            ) for i in range(1, 6)],
            spacing=0, tight=True,
        )

        summary = ft.Text(
            f"{avg:.1f} из 5 · {count} {'оценка' if count % 10 == 1 and count % 100 != 11 else 'оценки' if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14) else 'оценок'}" if count else "Пока нет оценок",
            size=12, color=ft.colors.ON_SURFACE_VARIANT,
        )

        clear_btn = ft.TextButton("Снять оценку", on_click=lambda e: self._clear_rating(lib_id)) if my else ft.Container()

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Оценить библиотеку", size=13, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    summary,
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([stars, clear_btn], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=4),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            bgcolor=ft.colors.SECONDARY_CONTAINER,
            border_radius=12,
        )

    def _load_rating(self, lib_id: str, callback):
        def _do():
            try:
                from src.core.firebase_client import firebase_client
                rating = firebase_client.get_library_rating(lib_id) or {}
            except Exception:
                rating = {}
            callback(rating)
        threading.Thread(target=_do, daemon=True).start()

    def _set_rating_loaded(self, lib_id: str, rating: dict):
        self._current_rating = rating
        if self._current_lib is not None and self._current_lib.get("id") == lib_id:
            self._build_library_detail()
            self.page.update()

    def _set_rating(self, lib_id: str, rating: int):
        def _do():
            try:
                from src.core.firebase_client import firebase_client
                new_rating = firebase_client.rate_library(lib_id, rating) or {}
                self._current_rating = new_rating
                self._rebuild_list_view()
                if self._current_lib is not None:
                    self._build_library_detail()
                self.page.update()
            except Exception:
                self._notify("Ошибка", "Не удалось поставить оценку", "error")
        threading.Thread(target=_do, daemon=True).start()

    def _clear_rating(self, lib_id: str):
        def _do():
            try:
                from src.core.firebase_client import firebase_client
                new_rating = firebase_client.remove_library_rating(lib_id) or {}
                self._current_rating = new_rating
                self._rebuild_list_view()
                if self._current_lib is not None:
                    self._build_library_detail()
                self.page.update()
            except Exception:
                self._notify("Ошибка", "Не удалось снять оценку", "error")
        threading.Thread(target=_do, daemon=True).start()

    def _read_book(self, book):
        if self.on_read_book:
            self.on_read_book(book)

    def _copy_invite(self, code: str):
        try:
            self.page.set_clipboard(code)
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Код {code} скопирован"), action="OK")
            self.page.snack_bar.open = True
            self.page.update()
        except Exception:
            pass

    # ---------- Создание / вступление ----------

    def _show_create_dialog(self, e=None):
        self._lib_title_field = ft.TextField(label="Название библиотеки", autofocus=True)
        self._lib_desc_field = ft.TextField(label="Описание (необязательно)", multiline=True, min_lines=2, max_lines=4)
        self._lib_visibility = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="public", label="Публичная"),
                ft.Radio(value="private", label="Приватная"),
            ]),
            value="public",
        )
        dlg = ft.AlertDialog(
            title=ft.Text("Новая библиотека"),
            content=ft.Column([
                self._lib_title_field,
                self._lib_desc_field,
                ft.Text("Доступ:", size=12, color=ft.colors.GREY),
                self._lib_visibility,
            ], tight=True, spacing=12, width=380),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.close(dlg)),
                ft.ElevatedButton("Создать", icon=ft.icons.CHECK, on_click=lambda _: self._create_library(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)
        self.page.update()

    def _create_library(self, dlg):
        title = (self._lib_title_field.value or "").strip()
        if not title:
            self._lib_title_field.error_text = "Введите название"
            self.page.update()
            return
        desc = (self._lib_desc_field.value or "").strip()
        vis = self._lib_visibility.value or "public"

        def _do():
            try:
                from src.core.firebase_client import firebase_client
                lib = firebase_client.create_library(title, desc, vis, [])
                self.page.close(dlg)
                if lib:
                    self._notify("Библиотека создана", f"Код приглашения: {lib.get('inviteCode', '')}", "success")
                self._refresh()
            except Exception as e:
                self._notify("Ошибка", f"Не удалось создать библиотеку: {e}", "error")
        threading.Thread(target=_do, daemon=True).start()

    def _show_join_dialog(self, e=None):
        self._join_code_field = ft.TextField(label="Код приглашения", autofocus=True, hint_text="Например: ABC123")
        dlg = ft.AlertDialog(
            title=ft.Text("Вступить в библиотеку"),
            content=self._join_code_field,
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.close(dlg)),
                ft.ElevatedButton("Вступить", icon=ft.icons.CHECK, on_click=lambda _: self._join_by_code(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)
        self.page.update()

    def _join_by_code(self, dlg):
        code = (self._join_code_field.value or "").strip().upper()
        if not code:
            return

        def _do():
            try:
                from src.core.firebase_client import firebase_client
                libs = firebase_client.get_libraries()
                target = next((lib for lib in libs if lib.get("inviteCode") == code), None)
                if target is None:
                    self.page.snack_bar = ft.SnackBar(content=ft.Text("Библиотека с таким кодом не найдена"), bgcolor=ft.colors.ERROR)
                    self.page.snack_bar.open = True
                    self.page.update()
                    return
                ok = firebase_client.join_library(target["id"], code)
                self.page.close(dlg)
                if ok:
                    self._notify("Вы вступили", f"Добро пожаловать в «{target.get('title', '')}»", "success")
                self._refresh()
            except Exception as e:
                self._notify("Ошибка", f"Не удалось вступить: {e}", "error")
        threading.Thread(target=_do, daemon=True).start()

    # ---------- Управление книгами библиотеки ----------

    def _show_add_book_dialog(self, e=None):
        lib = self._current_lib
        if not lib:
            return
        current_ids = set(int(b) for b in lib.get("bookIds", []))
        available = [b for b in self._all_books if b.id not in current_ids]
        if not available:
            self._notify("Нет книг", "Все книги уже в библиотеке или каталог пуст", "info")
            return
        self._book_dropdown = ft.Dropdown(
            label="Выберите книгу",
            options=[ft.dropdown.Option(key=str(b.id), text=f"{b.title} — {b.author}") for b in available],
            autofocus=True,
        )
        dlg = ft.AlertDialog(
            title=ft.Text("Добавить книгу"),
            content=self._book_dropdown,
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.close(dlg)),
                ft.ElevatedButton("Добавить", icon=ft.icons.CHECK, on_click=lambda _: self._add_book(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)
        self.page.update()

    def _add_book(self, dlg):
        book_id = self._book_dropdown.value
        if not book_id:
            return
        lib_id = self._current_lib.get("id")

        def _do():
            try:
                from src.core.firebase_client import firebase_client
                firebase_client.add_book_to_library(lib_id, int(book_id))
                self.page.close(dlg)
                lib = firebase_client.get_library(lib_id)
                self._current_lib = lib or self._current_lib
                self._build_library_detail()
                self.page.update()
            except Exception as e:
                self._notify("Ошибка", f"Не удалось добавить книгу: {e}", "error")
        threading.Thread(target=_do, daemon=True).start()

    def _remove_book(self, lib_id: str, book_id: int):
        def _do():
            try:
                from src.core.firebase_client import firebase_client
                firebase_client.remove_book_from_library(lib_id, book_id)
                lib = firebase_client.get_library(lib_id)
                self._current_lib = lib or self._current_lib
                self._build_library_detail()
                self.page.update()
            except Exception as e:
                self._notify("Ошибка", f"Не удалось убрать книгу: {e}", "error")
        threading.Thread(target=_do, daemon=True).start()

    def _confirm_delete_library(self, e=None):
        lib = self._current_lib
        if not lib:
            return
        dlg = ft.AlertDialog(
            title=ft.Text("Удалить библиотеку?"),
            content=ft.Text(f"Библиотека «{lib.get('title', '')}» будет удалена навсегда."),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.page.close(dlg)),
                ft.TextButton("Удалить", style=ft.ButtonStyle(color=ft.colors.RED),
                              on_click=lambda _: self._delete_library(lib.get("id"), dlg)),
            ],
        )
        self.page.open(dlg)
        self.page.update()

    def _delete_library(self, lib_id: str, dlg):
        def _do():
            try:
                from src.core.firebase_client import firebase_client
                firebase_client.delete_library(lib_id)
                self.page.close(dlg)
                self._current_lib = None
                self._refresh()
            except Exception as e:
                self._notify("Ошибка", f"Не удалось удалить библиотеку: {e}", "error")
        threading.Thread(target=_do, daemon=True).start()

    def build(self) -> ft.Control:
        return self.content
