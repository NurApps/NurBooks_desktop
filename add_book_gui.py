import os
import sys
from tkinter import messagebox, ttk

import customtkinter as ctk
import requests

# Добавляем путь к src для импорта моделей
sys.path.insert(0, os.path.abspath('.'))

from src.config import DEFAULT_DATA_PATH, DEFAULT_PDFS_PATH
from src.core.database import Database
from src.core.models import Book

# Настройка темы custom tkinter
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class BookManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Менеджер книг NurBooks")
        self.root.geometry("1920x1080")

        self.db = Database()
        self.selected_book_id = None  # Для отслеживания выбранной книги
        self.current_widget = None  # Для отслеживания текущего виджета

        # Создаём необходимые папки
        self.pdfs_path = DEFAULT_PDFS_PATH
        self.thumbnails_path = os.path.join(DEFAULT_DATA_PATH, "thumbnails")
        os.makedirs(self.pdfs_path, exist_ok=True)
        os.makedirs(self.thumbnails_path, exist_ok=True)

        self.create_widgets()
        self.setup_shortcuts()
        self.refresh_books_list()

    def create_widgets(self):
        # Заголовок
        title_label = ctk.CTkLabel(self.root, text="Менеджер книг NurBooks", font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=10)

        # Фрейм для формы
        form_frame = ctk.CTkFrame(self.root)
        form_frame.pack(pady=10, padx=20, fill=ctk.X)

        # Поле для ID
        id_label = ctk.CTkLabel(form_frame, text="ID книги:")
        id_label.grid(row=0, column=0, sticky=ctk.W, pady=5)
        vcmd = (self.root.register(self.validate_id), '%P')
        self.id_entry = ctk.CTkEntry(form_frame, width=400, validate='key', validatecommand=vcmd)
        self.id_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
        self._setup_widget_shortcuts(self.id_entry)

        # Поле для названия
        title_label = ctk.CTkLabel(form_frame, text="Название:")
        title_label.grid(row=1, column=0, sticky=ctk.W, pady=5)
        self.title_entry = ctk.CTkEntry(form_frame, width=400)
        self.title_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
        self._setup_widget_shortcuts(self.title_entry)

        # Поле для автора
        author_label = ctk.CTkLabel(form_frame, text="Автор:")
        author_label.grid(row=2, column=0, sticky=ctk.W, pady=5)
        self.author_entry = ctk.CTkEntry(form_frame, width=400)
        self.author_entry.grid(row=2, column=1, pady=5, padx=(10, 0))
        self._setup_widget_shortcuts(self.author_entry)

        # Поле для категории
        category_label = ctk.CTkLabel(form_frame, text="Категория:")
        category_label.grid(row=3, column=0, sticky=ctk.W, pady=5)
        self.category_entry = ctk.CTkEntry(form_frame, width=400)
        self.category_entry.grid(row=3, column=1, pady=5, padx=(10, 0))
        self._setup_widget_shortcuts(self.category_entry)

        # Поле для года
        year_label = ctk.CTkLabel(form_frame, text="Год:")
        year_label.grid(row=4, column=0, sticky=ctk.W, pady=5)
        self.year_entry = ctk.CTkEntry(form_frame, width=400)
        self.year_entry.grid(row=4, column=1, pady=5, padx=(10, 0))
        self._setup_widget_shortcuts(self.year_entry)

        # Поле для размера файла (МБ)
        file_size_label = ctk.CTkLabel(form_frame, text="Размер файла (МБ):")
        file_size_label.grid(row=5, column=0, sticky=ctk.W, pady=5)
        self.file_size_entry = ctk.CTkEntry(form_frame, width=400)
        self.file_size_entry.grid(row=5, column=1, pady=5, padx=(10, 0))
        self._setup_widget_shortcuts(self.file_size_entry)

        # Поле для количества страниц
        pages_label = ctk.CTkLabel(form_frame, text="Количество страниц:")
        pages_label.grid(row=6, column=0, sticky=ctk.W, pady=5)
        self.pages_entry = ctk.CTkEntry(form_frame, width=400)
        self.pages_entry.grid(row=6, column=1, pady=5, padx=(10, 0))
        self._setup_widget_shortcuts(self.pages_entry)

        copyright_label = ctk.CTkLabel(form_frame, text="Защищено авторскими правами:")
        copyright_label.grid(row=7, column=0, sticky=ctk.W, pady=5)
        self.copyright_protected_var = ctk.BooleanVar(value=False)
        self.copyright_protected_switch = ctk.CTkSwitch(
            form_frame,
            text="Да",
            variable=self.copyright_protected_var,
            onvalue=True,
            offvalue=False,
        )
        self.copyright_protected_switch.grid(row=7, column=1, sticky=ctk.W, pady=5, padx=(10, 0))

        # Поле для описания
        description_label = ctk.CTkLabel(form_frame, text="Описание:")
        description_label.grid(row=8, column=0, sticky=ctk.W, pady=5)
        self.description_text = ctk.CTkTextbox(form_frame, width=400, height=80)
        self.description_text.grid(row=8, column=1, pady=5, padx=(10, 0))
        self._setup_widget_shortcuts(self.description_text)

        # Поле для PDF (URL или локальный путь)
        pdf_url_label = ctk.CTkLabel(form_frame, text="PDF (URL или путь):")
        pdf_url_label.grid(row=9, column=0, sticky=ctk.W, pady=5)
        self.pdf_url_entry = ctk.CTkEntry(form_frame, width=400, placeholder_text="https://... или C:/path/to/file.pdf")
        self.pdf_url_entry.grid(row=9, column=1, pady=5, padx=(10, 0))
        self._setup_widget_shortcuts(self.pdf_url_entry)

        # Поле для обложки (URL или локальный путь)
        cover_url_label = ctk.CTkLabel(form_frame, text="Обложка (URL или путь):")
        cover_url_label.grid(row=10, column=0, sticky=ctk.W, pady=5)
        self.cover_url_entry = ctk.CTkEntry(form_frame, width=400, placeholder_text="https://... или C:/path/to/image.jpg")
        self.cover_url_entry.grid(row=10, column=1, pady=5, padx=(10, 0))
        self._setup_widget_shortcuts(self.cover_url_entry)

        # Индикатор прогресса
        self.progress_label = ctk.CTkLabel(form_frame, text="", text_color="blue")
        self.progress_label.grid(row=11, column=0, columnspan=2, pady=5)

        # Кнопки управления
        button_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        button_frame.pack(pady=10)

        self.add_button = ctk.CTkButton(
            button_frame,
            text="Добавить книгу",
            command=self.add_book,
            fg_color="#4CAF50",
            hover_color="#45a049",
            font=ctk.CTkFont(size=14)
        )
        self.add_button.grid(row=0, column=0, padx=5)

        self.update_button = ctk.CTkButton(
            button_frame,
            text="Обновить книгу",
            command=self.update_book,
            fg_color="#FF9800",
            hover_color="#e68900",
            font=ctk.CTkFont(size=14)
        )
        self.update_button.grid(row=0, column=1, padx=5)

        self.delete_button = ctk.CTkButton(
            button_frame,
            text="Удалить книгу",
            command=self.delete_book,
            fg_color="#F44336",
            hover_color="#d32f2f",
            font=ctk.CTkFont(size=14)
        )
        self.delete_button.grid(row=0, column=2, padx=5)

        self.clear_button = ctk.CTkButton(
            button_frame,
            text="Очистить форму",
            command=self.clear_form,
            fg_color="#9E9E9E",
            hover_color="#757575",
            font=ctk.CTkFont(size=14)
        )
        self.clear_button.grid(row=0, column=3, padx=5)

        self.reset_db_button = ctk.CTkButton(
            button_frame,
            text="Сбросить базу данных",
            command=self.reset_db,
            fg_color="#005AD8",
            hover_color="#0044a8",
            font=ctk.CTkFont(size=14)
        )
        self.reset_db_button.grid(row=0, column=4, padx=5)

        # Фрейм для списка книг
        list_frame = ctk.CTkFrame(self.root)
        list_frame.pack(pady=20, padx=20, fill=ctk.BOTH, expand=True)

        # Заголовок списка
        list_title = ctk.CTkLabel(list_frame, text="Существующие книги", font=ctk.CTkFont(size=16, weight="bold"))
        list_title.pack(anchor=ctk.NW, padx=10, pady=(10, 5))

        # Создаем Treeview для отображения книг (используем стандартный ttk для Treeview)
        columns = ("ID", "Название", "Автор", "Категория", "Год", "Размер (МБ)", "Страницы", "Авторские права", "PDF")

        # Настройка стиля Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", rowheight=25)
        style.map("Treeview", background=[("selected", "#1f6aa5")])
        style.configure("Treeview.Heading", background="#444444", foreground="white", font=("Arial", 10, "bold"))

        self.books_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10, style="Treeview")

        # Настройка заголовков
        for col in columns:
            self.books_tree.heading(col, text=col)
            self.books_tree.column(col, width=100)

        # Добавляем виджет Treeview
        self.books_tree.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, pady=5, padx=(10, 0))

        # Добавляем вертикальный скроллбар
        scrollbar = ttk.Scrollbar(list_frame, orient=ctk.VERTICAL, command=self.books_tree.yview)
        self.books_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=ctk.RIGHT, fill=ctk.Y, padx=(0, 10), pady=5)

        # Привязываем событие выбора строки
        self.books_tree.bind("<<TreeviewSelect>>", self.on_book_select)

    def _setup_widget_shortcuts(self, widget):
        """Настройка горячих клавиш и контекстного меню для виджета"""
        widget.bind("<FocusIn>", lambda e: self._on_widget_focus(widget))
        widget.bind("<Button-3>", lambda e: self._show_context_menu(e, widget))

    def _on_widget_focus(self, widget):
        """Обновляем текущий виджет при получении фокуса"""
        self.current_widget = widget

    def _show_context_menu(self, event, widget):
        """Показываем контекстное меню при правом клике"""
        from tkinter import Menu
        menu = Menu(self.root, tearoff=0)

        menu.add_command(label="Копировать", command=lambda: self._copy_from_widget(widget))
        menu.add_command(label="Вставить", command=lambda: self._paste_to_widget(widget))
        menu.add_separator()
        menu.add_command(label="Выделить всё", command=lambda: self._select_all_in_widget(widget))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copy_from_widget(self, widget):
        """Копирует текст из виджета в буфер обмена"""
        try:
            if isinstance(widget, ctk.CTkEntry):
                text = widget.get()
            else:
                try:
                    text = widget.get("sel.first", "sel.last")
                except Exception:
                    text = widget.get("1.0", ctk.END).strip()

            if text:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                self.root.update()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать: {str(e)}")

    def _paste_to_widget(self, widget):
        """Вставляет текст из буфера обмена в виджет"""
        try:
            text = self.root.clipboard_get()

            if isinstance(widget, ctk.CTkEntry):
                widget.insert(ctk.INSERT, text)
            else:
                widget.insert(ctk.INSERT, text)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось вставить: {str(e)}")

    def _select_all_in_widget(self, widget):
        """Выделяет весь текст в виджете"""
        try:
            if isinstance(widget, ctk.CTkEntry):
                widget.select_range(0, ctk.END)
                widget.icursor(ctk.END)
            else:
                widget.tag_add("sel", "1.0", ctk.END)
                widget.mark_set(ctk.INSERT, "1.0")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось выделить: {str(e)}")

    def setup_shortcuts(self):
        """Настройка глобальных горячих клавиш"""
        self.root.bind("<Control-c>", self._on_ctrl_c)
        self.root.bind("<Control-v>", self._on_ctrl_v)
        self.root.bind("<Control-a>", self._on_ctrl_a)

    def _on_ctrl_c(self, event):
        """Обработка Ctrl+C - копирование"""
        if self.current_widget:
            self._copy_from_widget(self.current_widget)
        return "break"

    def _on_ctrl_v(self, event):
        """Обработка Ctrl+V - вставка"""
        if self.current_widget:
            self._paste_to_widget(self.current_widget)
        return "break"

    def _on_ctrl_a(self, event):
        """Обработка Ctrl+A - выделение всего"""
        if self.current_widget:
            self._select_all_in_widget(self.current_widget)
        return "break"

    def _convert_to_raw_url(self, url: str) -> str:
        """Конвертирует GitHub URL в raw URL для прямого доступа к файлу"""
        if not url:
            return url

        # Поддержка GitHub Releases (новый формат)
        # https://github.com/salihhhh014/NurBooks/releases/download/COVERS/filename.png
        if "github.com" in url and "/releases/download/" in url:
            # Для Releases уже raw-адреса - просто возвращаем как есть
            return url

        # Поддержка GitHub blob (старый формат)
        if "github.com" in url and "/blob/" in url:
            return url.replace("/blob/", "/raw/")
        return url

    def _check_url_exists(self, url: str, file_type: str = "файл") -> bool:
        """
        Проверяет существование файла по URL.
        Обновлен для корректной работы с GitHub Releases (добавлен User-Agent).
        """
        if not url:
             return False

        try:
            # Конвертируем URL в правильный формат (например, blob -> raw)
            url = self._convert_to_raw_url(url)

            self.progress_label.configure(text=f"Проверка доступности {file_type}...")
            self.root.update()

            # Добавляем User-Agent, чтобы GitHub не блокировал скрипт
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

            # Сначала пробуем быстрый метод (HEAD)
            try:
                response = requests.head(url, timeout=15, allow_redirects=True, headers=headers)
                if response.status_code < 400:
                    self.progress_label.configure(text=f"✅ {file_type.capitalize()} доступен!")
                    return True
            except Exception:
                pass

            # Если HEAD провалился (частично устаревшие ссылки GitHub), пробуем надежный GET
            response = requests.get(url, timeout=30, allow_redirects=True, headers=headers)

            if response.status_code == 200:
                self.progress_label.configure(text=f"✅ {file_type.capitalize()} доступен!")
                return True

            self.progress_label.configure(text="")
            messagebox.showerror("Ошибка проверки", f"{file_type.capitalize()} не найден.\n\nУбедитесь, что ссылка является прямой ссылкой на файл (не на страницу GitHub).\nКод ошибки: {response.status_code}")
            return False

        except Exception as e:
            self.progress_label.configure(text="")
            messagebox.showerror("Ошибка сети", f"Не удалось проверить {file_type}:\n{str(e)}")
            return False

    def _download_file(self, url: str, save_path: str, file_type: str = "файл") -> bool:
        """
        Скачивает файл по URL и сохраняет по указанному пути.
        """
        if not url:
             return False

        try:
            # Конвертируем GitHub URL в raw формат
            url = self._convert_to_raw_url(url)

            self.progress_label.configure(text=f"Скачивание {file_type}...")
            self.root.update()

            # Добавляем User-Agent, чтобы GitHub разрешал скачивание
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

            response = requests.get(url, timeout=60, headers=headers)
            response.raise_for_status()

            with open(save_path, 'wb') as f:
                f.write(response.content)

            self.progress_label.configure(text=f"✅ {file_type.capitalize()} успешно скачан!")
            return True

        except requests.exceptions.RequestException as e:
            self.progress_label.configure(text="")
            messagebox.showerror("Ошибка скачивания", f"Не удалось скачать {file_type}:\n{str(e)}")
            return False
        except Exception as e:
            self.progress_label.configure(text="")
            messagebox.showerror("Ошибка", f"Произошла ошибка при скачивании {file_type}:\n{str(e)}")
            return False

    def _get_filename_from_url(self, url: str, book_id: int, extension: str) -> str:
        """
        Извлекает имя файла из URL или генерирует его на основе ID книги

        Args:
            url: URL файла
            book_id: ID книги
            extension: Расширение файла (например, '.pdf', '.jpg')

        Returns:
            str: Имя файла
        """
        try:
            # Убираем query параметры из URL
            clean_url = url.split('?')[0]
            filename = os.path.basename(clean_url)

            if filename and '.' in filename:
                return filename
        except Exception:
            pass

        # Если не удалось извлечь имя, генерируем на основе ID
        return f"book_{book_id}{extension}"

    def validate_id(self, new_value):
        """Валидация для поля ID: допускаются только цифры (или пустая строка)."""
        return new_value.isdigit() or new_value == ""

    def add_book(self):
        """
        Добавляет новую книгу.
        НЕ скачивает файлы - только проверяет доступность URL и сохраняет ссылки как есть.
        Если файл уже существует локально, оставляет локальный путь без изменений.
        """
        try:
            id_str = self.id_entry.get().strip()
            if id_str == "":
                messagebox.showerror("Ошибка", "ID обязателен и должен содержать только цифры.")
                return
            if not id_str.isdigit():
                messagebox.showerror("Ошибка", "ID должен содержать только цифры.")
                return

            book_id = int(id_str)

            # Ранняя проверка уникальности ID
            if self.db.get_book_by_id(book_id):
                messagebox.showerror("Ошибка", f"Книга с ID {book_id} уже существует.")
                return

            title = self.title_entry.get().strip()
            author = self.author_entry.get().strip()
            category = self.category_entry.get().strip()
            year = int(self.year_entry.get()) if self.year_entry.get().strip() else 0
            file_size = self.file_size_entry.get().strip() if self.file_size_entry.get().strip() else None
            pages = int(self.pages_entry.get()) if self.pages_entry.get().strip() else 0
            description = self.description_text.get("1.0", ctk.END).strip()
            pdf_url = self.pdf_url_entry.get().strip()
            cover_url = self.cover_url_entry.get().strip()

            if not title or not author or not pdf_url:
                messagebox.showerror("Ошибка", "Пожалуйста, заполните все обязательные поля: ID, название, автор и ссылка на PDF.")
                return

            # Обрабатываем PDF - всегда сохраняем URL как есть
            pdf_path = pdf_url
            if pdf_url.startswith(('http://', 'https://')):
                # Это URL - проверяем доступность без скачивания
                if not self._check_url_exists(pdf_url, "PDF"):
                    return
                # Сохраняем URL как есть
                pdf_path = pdf_url
            else:
                # Локальный путь или что-то другое - сохраняем как есть без изменений
                pdf_path = pdf_url

            # Обрабатываем обложку - всегда сохраняем URL как есть
            cover_path = cover_url
            if cover_url:
                if cover_url.startswith(('http://', 'https://')):
                    # Это URL - проверяем доступность без скачивания
                    if not self._check_url_exists(cover_url, "обложка"):
                        # Если обложка недоступна, продолжаем без неё
                        cover_path = ""
                    else:
                        # Сохраняем URL как есть
                        cover_path = cover_url
                else:
                    # Локальный путь или что-то другое - сохраняем как есть без изменений
                    cover_path = cover_url

            new_book = Book(
                id=book_id,
                title=title,
                author=author,
                category=category,
                year=year,
                file_size=file_size,
                pages=pages,
                description=description,
                cover=cover_path,
                pdf=pdf_path,
                copyright_protected=self.copyright_protected_var.get() if hasattr(self, "copyright_protected_var") else False
            )

            result = self.db.add_book(new_book)
            if result == "success":
                messagebox.showinfo("Успех", f"Книга '{title}' успешно добавлена!\n\nPDF: {pdf_path}\nОбложка: {cover_path if cover_path else 'не указана'}")
                self.refresh_books_list()
                self.clear_form()
            elif result == "id_exists":
                messagebox.showerror("Ошибка", f"Книга с ID {book_id} уже существует.")
            elif result == "pdf_exists":
                messagebox.showerror("Ошибка", "Книга с таким PDF уже существует.")
            else:
                messagebox.showerror("Ошибка", "Произошла ошибка при добавлении книги.")

        except ValueError:
            messagebox.showerror("Ошибка", "Год и количество страниц должны быть числами.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при добавлении книги: {str(e)}")
        finally:
            self.progress_label.configure(text="")

    def update_book(self):
        """
        Обновляет информацию о книге.
        НЕ скачивает файлы - только проверяет доступность URL и сохраняет ссылки как есть.
        """
        try:
            if self.selected_book_id is None:
                messagebox.showerror("Ошибка", "Пожалуйста, выберите книгу из списка для обновления.")
                return

            book_id = self.selected_book_id
            title = self.title_entry.get().strip()
            author = self.author_entry.get().strip()
            category = self.category_entry.get().strip()
            year = int(self.year_entry.get()) if self.year_entry.get().strip() else 0
            file_size = self.file_size_entry.get().strip() if self.file_size_entry.get().strip() else None
            pages = int(self.pages_entry.get()) if self.pages_entry.get().strip() else 0
            description = self.description_text.get("1.0", ctk.END).strip()
            pdf_url = self.pdf_url_entry.get().strip()
            cover_url = self.cover_url_entry.get().strip()

            if not title or not author:
                messagebox.showerror("Ошибка", "Пожалуйста, заполните все обязательные поля: название и автор.")
                return

            # Получаем текущую книгу (для сохранения старых значений если поле пустое)
            current_book = self.db.get_book_by_id(book_id)

            # Обрабатываем PDF - всегда сохраняем как есть
            pdf_path = pdf_url
            if pdf_url.startswith(('http://', 'https://')):
                # Это URL - проверяем доступность без скачивания
                if not self._check_url_exists(pdf_url, "PDF"):
                    return
                # Сохраняем URL как есть
                pdf_path = pdf_url
            elif pdf_url:
                # Локальный путь или что-то другое - сохраняем как есть без изменений
                pdf_path = pdf_url
            else:
                # Если поле пустое, оставляем старое значение
                pdf_path = current_book.pdf if current_book else ""

            # Обрабатываем обложку - всегда сохраняем как есть
            cover_path = cover_url
            if cover_url:
                if cover_url.startswith(('http://', 'https://')):
                    # Это URL - проверяем доступность без скачивания
                    if not self._check_url_exists(cover_url, "обложка"):
                        # Если обложка недоступна, оставляем старое значение
                        cover_path = current_book.cover if current_book else ""
                    else:
                        # Сохраняем URL как есть
                        cover_path = cover_url
                else:
                    # Локальный путь или что-то другое - сохраняем как есть без изменений
                    cover_path = cover_url
            else:
                # Если поле пустое, оставляем старое значение
                cover_path = current_book.cover if current_book else ""

            updated_book = Book(
                id=book_id,
                title=title,
                author=author,
                category=category,
                year=year,
                file_size=file_size,
                pages=pages,
                description=description,
                cover=cover_path,
                pdf=pdf_path,
                copyright_protected=self.copyright_protected_var.get() if hasattr(self, "copyright_protected_var") else False
            )

            result = self.db.update_book(updated_book)
            if result:
                messagebox.showinfo("Успех", f"Книга '{title}' успешно обновлена!\n\nPDF: {pdf_path}\nОбложка: {cover_path if cover_path else 'не указана'}")
                self.refresh_books_list()
                self.clear_form()
            else:
                # Проверяем, не связан ли PDF с другой книгой
                existing_book = self.db.get_book_by_pdf(pdf_path)
                if existing_book and existing_book.id != book_id:
                    messagebox.showerror("Ошибка", f"Этот PDF уже привязан к другой книге:\n\nID: {existing_book.id}\nНазвание: {existing_book.title}\n\nИспользуйте другой URL для PDF.")
                else:
                    messagebox.showerror("Ошибка", "Не удалось обновить книгу. Возможно, возникла проблема с базой данных или книга не найдена.")

        except ValueError:
            messagebox.showerror("Ошибка", "Год и количество страниц должны быть числами.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при обновлении книги: {str(e)}")
        finally:
            self.progress_label.configure(text="")

    def delete_book(self):
        try:
            if self.selected_book_id is None:
                messagebox.showerror("Ошибка", "Пожалуйста, выберите книгу из списка для удаления.")
                return

            result = messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить книгу с ID {self.selected_book_id}?")
            if not result:
                return

            # Получаем книгу для удаления файлов
            book = self.db.get_book_by_id(self.selected_book_id)
            pdf_path = book.pdf if book else None
            cover_path = book.cover if book else None

            # Удаляем книгу из базы данных по ID (более надёжно)
            if self.db.delete_book_by_id(self.selected_book_id):
                # Удаляем локальные файлы
                if pdf_path and os.path.exists(pdf_path):
                    try:
                        os.remove(pdf_path)
                    except Exception as e:
                        print(f"Не удалось удалить PDF файл: {e}")

                if cover_path and os.path.exists(cover_path):
                    try:
                        os.remove(cover_path)
                    except Exception as e:
                        print(f"Не удалось удалить файл обложки: {e}")

                messagebox.showinfo("Успех", "Книга успешно удалена!")
                self.refresh_books_list()
                self.clear_form()
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить книгу.")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при удалении книги: {str(e)}")

    def refresh_books_list(self):
        for item in self.books_tree.get_children():
            self.books_tree.delete(item)

        books = self.db.get_all_books()
        for book in books:
            self.books_tree.insert(
                "",
                ctk.END,
                values=(
                    book.id,
                    book.title,
                    book.author,
                    book.category,
                    book.year,
                    book.file_size,
                    book.pages,
                    "Да" if getattr(book, "copyright_protected", False) else "Нет",
                    book.pdf,
                ),
            )

    def on_book_select(self, event):
        selection = self.books_tree.selection()
        if selection:
            item = self.books_tree.item(selection[0])
            values = item['values']

            selected_id = values[0]
            selected_book = self.db.get_book_by_id(selected_id)

            if selected_book:
                self.selected_book_id = selected_book.id
                self.id_entry.configure(state="normal")
                self.id_entry.delete(0, ctk.END)
                self.id_entry.insert(0, selected_book.id)
                self.id_entry.configure(state="readonly")

                self.title_entry.delete(0, ctk.END)
                self.title_entry.insert(0, selected_book.title)
                self.author_entry.delete(0, ctk.END)
                self.author_entry.insert(0, selected_book.author)
                self.category_entry.delete(0, ctk.END)
                self.category_entry.insert(0, selected_book.category)
                self.year_entry.delete(0, ctk.END)
                self.year_entry.insert(0, str(selected_book.year))
                self.description_text.delete("1.0", ctk.END)
                self.description_text.insert("1.0", selected_book.description)

                # Показываем локальные пути (для информации)
                self.pdf_url_entry.delete(0, ctk.END)
                self.pdf_url_entry.insert(0, selected_book.pdf)
                self.cover_url_entry.delete(0, ctk.END)
                self.cover_url_entry.insert(0, selected_book.cover)

                self.file_size_entry.delete(0, ctk.END)
                self.file_size_entry.insert(0, selected_book.file_size or "")
                self.pages_entry.delete(0, ctk.END)
                self.pages_entry.insert(0, str(selected_book.pages) if selected_book.pages else "")
                if hasattr(self, "copyright_protected_var"):
                    self.copyright_protected_var.set(bool(getattr(selected_book, "copyright_protected", False)))

    def clear_form(self):
        self.id_entry.configure(state="normal")
        self.id_entry.delete(0, ctk.END)
        self.title_entry.delete(0, ctk.END)
        self.author_entry.delete(0, ctk.END)
        self.category_entry.delete(0, ctk.END)
        self.year_entry.delete(0, ctk.END)
        self.file_size_entry.delete(0, ctk.END)
        self.pages_entry.delete(0, ctk.END)
        if hasattr(self, "copyright_protected_var"):
            self.copyright_protected_var.set(False)
        self.description_text.delete("1.0", ctk.END)
        self.pdf_url_entry.delete(0, ctk.END)
        self.cover_url_entry.delete(0, ctk.END)
        self.progress_label.configure(text="")
        self.selected_book_id = None


    def reset_db(self):
        result = messagebox.askyesno("Подтверждение", "Вы уверены, что хотите сбросить базу данных книг? Все данные будут удалены.")
        if not result:
            return

        try:
            self.clear_form()
            for item in self.books_tree.get_children():
                self.books_tree.delete(item)

            self.db.clear_books()

            messagebox.showinfo("Успех", "База данных книг успешно сброшена!")
            self.refresh_books_list()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при сбросе базы данных: {str(e)}")



def main():
    root = ctk.CTk()
    BookManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
