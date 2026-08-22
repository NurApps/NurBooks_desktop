import os
import shutil
import tempfile
import threading
import zipfile
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pythoncom
import requests
import win32com.client

# Настройка темы custom tkinter
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("green")


class NurBooksInstaller:
    def __init__(self):
        self.root = ctk.CTk()
        self.setup_window()

    def setup_window(self):
        """Создание основного окна установщика"""
        self.root.title("Установка NurBooks")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        self.center_window()

        self.install_path = ctk.StringVar(value=os.path.join(os.environ['USERPROFILE'], 'NurBooks'))
        self.create_desktop_shortcut = ctk.BooleanVar(value=True)
        self.create_start_menu_shortcut = ctk.BooleanVar(value=True)
        self.launch_after_install = ctk.BooleanVar(value=True)

        self.create_widgets()

    def create_widgets(self):
        """Создание элементов интерфейса"""
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=20, pady=20)

        title_label = ctk.CTkLabel(
            main_frame,
            text="Установка NurBooks",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(0, 20))

        path_label = ctk.CTkLabel(main_frame, text="Путь установки:")
        path_label.pack(anchor=ctk.W, pady=(0, 5))

        path_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        path_frame.pack(fill=ctk.X, pady=(0, 15))

        path_entry = ctk.CTkEntry(path_frame, textvariable=self.install_path, width=320)
        path_entry.pack(side=ctk.LEFT, fill=ctk.X, expand=True, padx=(0, 10))

        browse_button = ctk.CTkButton(
            path_frame,
            text="Обзор...",
            command=self.browse_install_path,
            width=80
        )
        browse_button.pack(side=ctk.LEFT)

        desktop_checkbox = ctk.CTkCheckBox(
            main_frame,
            text="Создать ярлык на рабочем столе",
            variable=self.create_desktop_shortcut,
            border_color="#4CAF50",
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        desktop_checkbox.pack(anchor=ctk.W, pady=5)

        start_menu_checkbox = ctk.CTkCheckBox(
            main_frame,
            text="Создать ярлык в меню Пуск",
            variable=self.create_start_menu_shortcut,
            border_color="#4CAF50",
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        start_menu_checkbox.pack(anchor=ctk.W, pady=5)

        launch_checkbox = ctk.CTkCheckBox(
            main_frame,
            text="Запустить NurBooks после установки",
            variable=self.launch_after_install,
            border_color="#4CAF50",
            fg_color="#4CAF50",
            hover_color="#45a049"
        )
        launch_checkbox.pack(anchor=ctk.W, pady=5)

        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=20)

        install_button = ctk.CTkButton(
            button_frame,
            text="Установить",
            command=self.start_installation,
            fg_color="#4CAF50",
            hover_color="#45a049",
            width=120
        )
        install_button.pack(side=ctk.LEFT, padx=(0, 10))

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Отмена",
            command=self.root.quit,
            fg_color="#9E9E9E",
            hover_color="#757575",
            width=120
        )
        cancel_button.pack(side=ctk.LEFT)

        self.progress = ctk.CTkProgressBar(main_frame, width=400, progress_color="#4CAF50")
        self.progress.pack(pady=(10, 10))
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(
            main_frame,
            text="Готов к установке",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=(5, 0))

    def browse_install_path(self):
        path = filedialog.askdirectory(initialdir=self.install_path.get())
        if path:
            self.install_path.set(path)

    def start_installation(self):
        self.status_label.configure(text="Подготовка к установке...")
        self.progress.set(0)
        threading.Thread(target=self.perform_installation, daemon=True).start()

    def perform_installation(self):
        pythoncom.CoInitialize()

        DOWNLOAD_URL = "https://github.com/NurApps/NurBooks_desktop/releases/latest/download/nurbooks.zip"

        selected_dest_dir = self.install_path.get()
        dest_dir = os.path.join(selected_dest_dir, "NurBooks")

        try:
            # Удаление старых версий
            old_dirs = [
                os.path.join(selected_dest_dir, d)
                for d in os.listdir(selected_dest_dir)
                if os.path.isdir(os.path.join(selected_dest_dir, d)) and d.startswith("NurBooks-")
            ] if os.path.isdir(selected_dest_dir) else []
            for old_dir in old_dirs:
                try:
                    shutil.rmtree(old_dir)
                    print(f"Удалена старая версия: {old_dir}")
                except Exception as e:
                    print(f"Не удалось удалить {old_dir}: {e}")

            if os.path.exists(dest_dir):
                overwrite = messagebox.askyesno(
                    "Подтверждение",
                    f"Целевая папка уже существует:\n{dest_dir}\n\nПерезаписать?"
                )
                if not overwrite:
                    self.root.after(0, lambda: self.status_label.configure(text="Установка отменена пользователем"))
                    return
                else:
                    shutil.rmtree(dest_dir)

            os.makedirs(dest_dir, exist_ok=True)

            # 1. СКАЧИВАНИЕ
            self.root.after(0, lambda: self.status_label.configure(text="Скачивание NurBooks..."))

            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
                temp_zip_path = tmp_file.name

            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                response = requests.get(DOWNLOAD_URL, stream=True, headers=headers, allow_redirects=True)
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                block_size = 8192
                downloaded_size = 0

                with open(temp_zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=block_size):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            if total_size > 0:
                                progress = (downloaded_size / total_size) * 40
                                self.root.after(0, lambda pv=progress: self.progress.set(pv / 100))

                # 2. РАСПАКОВКА
                self.root.after(0, lambda: self.status_label.configure(text="Установка файлов..."))
                self.root.after(0, lambda: self.progress.set(0.45))

                with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    total_files = len(file_list)
                    for i, file in enumerate(file_list):
                        zip_ref.extract(file, dest_dir)
                        progress = 45 + ((i + 1) / total_files) * 45
                        self.root.after(0, lambda pv=progress: self.progress.set(pv / 100))

            finally:
                if os.path.exists(temp_zip_path):
                    os.remove(temp_zip_path)

            # 3. СОЗДАНИЕ ПАПОК
            os.makedirs(os.path.join(dest_dir, "downloads"), exist_ok=True)
            os.makedirs(os.path.join(dest_dir, "saved_books"), exist_ok=True)

            self.root.after(0, lambda: self.status_label.configure(text="Создание ярлыков..."))
            self.root.after(0, lambda: self.progress.set(0.95))

            # 4. УДАЛЕНИЕ СТАРЫХ ЯРЛЫКОВ
            self.remove_old_shortcuts()

            # 5. СОЗДАНИЕ ЯРЛЫКОВ
            exe_path = self._find_exe(dest_dir)
            desktop = self._get_desktop_dir()
            start_menu = os.path.join(
                os.environ['APPDATA'],
                'Microsoft', 'Windows', 'Start Menu', 'Programs'
            )

            if exe_path:
                if self.create_desktop_shortcut.get():
                    self._make_shortcut(
                        os.path.join(desktop, 'NurBooks.lnk'),
                        exe_path
                    )

                if self.create_start_menu_shortcut.get():
                    os.makedirs(start_menu, exist_ok=True)
                    self._make_shortcut(
                        os.path.join(start_menu, 'NurBooks.lnk'),
                        exe_path
                    )

                    # 6. ДЕИНСТАЛЯТОР + ярлык на него в меню Пуск
                    uninstall_cmd = os.path.join(dest_dir, "uninstall.cmd")
                    with open(uninstall_cmd, "w", encoding="cp866", errors="replace") as f:
                        f.write(self._build_uninstall_script(dest_dir))
                    self._make_shortcut(
                        os.path.join(start_menu, "Uninstall NurBooks.lnk"),
                        uninstall_cmd
                    )
            else:
                print("EXE файл не найден, ярлыки не созданы")

            # 7. ЗАПУСК ПОСЛЕ УСТАНОВКИ
            if self.launch_after_install.get() and exe_path:
                self.root.after(0, lambda p=exe_path: os.startfile(p))

            self.root.after(0, lambda: self.status_label.configure(text="Установка завершена успешно!"))
            self.root.after(0, lambda: self.progress.set(1))
            self.root.after(0, lambda: messagebox.showinfo(
                "Успех",
                f"Установка NurBooks завершена успешно!\n\nПрограмма установлена в:\n{dest_dir}"
            ))

        except Exception as e:
            self.root.after(0, lambda err=e: messagebox.showerror(
                "Ошибка", f"Произошла ошибка во время установки:\n{str(err)}"
            ))
            self.root.after(0, lambda: self.status_label.configure(text="Ошибка установки"))
        finally:
            pythoncom.CoUninitialize()

    def _find_exe(self, search_dir):
        """Поиск первого .exe файла в директории"""
        for root, dirs, files in os.walk(search_dir):
            for file in files:
                if file.endswith('.exe'):
                    return os.path.join(root, file)
        return None

    def _get_desktop_dir(self):
        """Реальный путь к рабочему столу (учитывает OneDrive/перенаправление)."""
        try:
            shell = win32com.client.Dispatch("WScript.Shell")
            return shell.SpecialFolders("Desktop")
        except Exception:
            return os.path.join(os.environ['USERPROFILE'], 'Desktop')

    def _build_uninstall_script(self, dest_dir):
        """Генерирует uninstall.cmd: удаляет папку установки и ярлыки."""
        desktop = self._get_desktop_dir()
        start_menu = os.path.join(
            os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs'
        )
        # cp866 (OEM) — чтобы cmd корректно выполнил файл с не-ASCII путями
        script = (
            "@echo off\r\n"
            "chcp 65001 >nul\r\n"
            "echo Zakrytie NurBooks...\r\n"
            "taskkill /f /im NurBooks.exe >nul 2>&1\r\n"
            "timeout /t 2 /nobreak >nul\r\n"
            f"del \"{os.path.join(desktop, 'NurBooks.lnk')}\" >nul 2>&1\r\n"
            f"del \"{os.path.join(start_menu, 'NurBooks.lnk')}\" >nul 2>&1\r\n"
            f"del \"%~dp0uninstall.cmd\" >nul 2>&1\r\n"
            "cd /d \"%USERPROFILE%\"\r\n"
            f"rd /s /q \"{dest_dir}\"\r\n"
            "echo NurBooks udalen.\r\n"
            "pause\r\n"
        )
        return script

    def _make_shortcut(self, shortcut_path, target_path):
        """Создание ярлыка через pywin32 (COM уже инициализирован в потоке)"""
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(shortcut_path)
        shortcut.TargetPath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        shortcut.IconLocation = target_path
        shortcut.Description = "NurBooks - Читательская библиотека"
        shortcut.Save()
        print(f"Ярлык создан: {shortcut_path}")

    def remove_old_shortcuts(self):
        """Удаление старых ярлыков NurBooks"""
        appdata = os.environ.get('APPDATA', '')
        desktop = self._get_desktop_dir()

        old_shortcuts = [
            os.path.join(desktop, 'NurBooks.lnk'),
            os.path.join(desktop, 'NurBooks 1.0.0.lnk'),
            os.path.join(desktop, 'NurBooks-1.0.0.lnk'),
            os.path.join(appdata, 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'NurBooks.lnk'),
            os.path.join(appdata, 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'NurBooks 1.0.0.lnk'),
            os.path.join(appdata, 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'NurBooks-1.0.0.lnk'),
            os.path.join(appdata, 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'NurBooks-1.2.75 Lite.lnk'),
        ]

        for shortcut in old_shortcuts:
            if os.path.exists(shortcut):
                try:
                    os.remove(shortcut)
                    print(f"Удалён старый ярлык: {shortcut}")
                except Exception as e:
                    print(f"Не удалось удалить {shortcut}: {e}")

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    installer = NurBooksInstaller()
    installer.run()
