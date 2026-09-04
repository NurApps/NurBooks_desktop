"""
Конфигурация приложения NurBooks
"""
import os
import sys
from pathlib import Path


def _load_env_file():
    """Загружает переменные окружения из .env (не перезаписывая уже заданные).

    Ищет .env: рядом с EXE, в корне проекта, в текущей папке.
    """
    candidates = []
    if getattr(sys, 'frozen', False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), ".env"))
    candidates.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
    candidates.append(".env")

    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
        except Exception:
            pass
        return


_load_env_file()

# API сервер — URL деплоя на Render
API_BASE_URL = os.environ.get("API_BASE_URL", "https://nurbooks-api.onrender.com")
# Ключ API сервера (NURBOOKS_API_KEY на Render). Держите в .env!
API_KEY = os.environ.get("NURBOOKS_API_KEY", "r4avD5b70owsl7W4qgkK-JrHvFPxy7ald_eJEifml2Q")

APP_NAME = "NurBooks"
APP_VERSION = "1.4.0  Beta"
APP_DESCRIPTION = "Электронная исламская библиотека от NurApps."
DEVELOPERS = ["Salikh Suyundikov", "Daniyal Kislicky"]
TESTERS = ["Mukhammad Odilov"]
DESIGNERS = ["Muslim Temirbekov"]
TELEGRAM_CONTACTS = ["@salih2014suyundikov"]
CONTACT_EMAIL = "salixsuyundikov@gmail.com"

# Определяем базовый путь. Если exe - папка с exe, иначе - текущая папка.
if getattr(sys, 'frozen', False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    BASE_PATH = os.path.abspath(".")

# Системная папка загрузок Windows (по умолчанию)
SYSTEM_DOWNLOADS_PATH = str(Path.home() / "Downloads")

# Папка для загрузок NurBooks в системной папке загрузок
NURBOOKS_DOWNLOADS_PATH = str(Path.home() / "Downloads" / "downloads-nurbooks")

# Пути по умолчанию
DEFAULT_DOWNLOAD_PATH = NURBOOKS_DOWNLOADS_PATH  # Используется отдельная папка downloads-nurbooks
DEFAULT_SAVE_PATH = os.path.join(BASE_PATH, "saved_books")
DEFAULT_DATA_PATH = os.path.join(BASE_PATH, "data")
DEFAULT_ASSETS_PATH = os.path.join(BASE_PATH, "assets")
DEFAULT_PDFS_PATH = os.path.join(BASE_PATH, "pdfs")
# Настройки отображения
ITEMS_PER_PAGE = 12

# Настройки электронной почты
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587
EMAIL_ADDRESS = ""
EMAIL_PASSWORD = ""

def _resolve_service_account_key():
    """Ищет serviceAccountKey.json: рядом с EXE, в _MEIPASS, в CWD"""
    candidates = []
    if getattr(sys, 'frozen', False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), "serviceAccountKey.json"))
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            candidates.append(os.path.join(meipass, "serviceAccountKey.json"))
    candidates.append(os.path.join(BASE_PATH, "serviceAccountKey.json"))
    candidates.append("serviceAccountKey.json")
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[-1]

SERVICE_ACCOUNT_KEY_PATH = _resolve_service_account_key()

# Настройки Firebase
class FirebaseConfig:
    """Конфигурация Firebase. Web API-ключ держите в .env (переменная FIREBASE_API_KEY)."""
    PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "nurbooks-3b694")
    API_KEY = os.environ.get("FIREBASE_API_KEY", "")
    AUTH_DOMAIN = os.environ.get("FIREBASE_AUTH_DOMAIN", "nurbooks-3b694.firebaseapp.com")
    MESSAGING_SENDER_ID = os.environ.get("FIREBASE_MESSAGING_SENDER_ID", "9086132352")
    APP_ID = os.environ.get("FIREBASE_APP_ID", "1:9086132352:web:fbed7cfafa2df0d4a20665")
    SERVICE_ACCOUNT_KEY_PATH = SERVICE_ACCOUNT_KEY_PATH

    @classmethod
    def to_dict(cls):
        """Возвращает конфигурацию в dict формате"""
        return {
            'projectId': cls.PROJECT_ID,
            'apiKey': cls.API_KEY,
            'authDomain': cls.AUTH_DOMAIN,
            'messagingSenderId': cls.MESSAGING_SENDER_ID,
            'appId': cls.APP_ID
        }

    @classmethod
    def is_configured(cls):
        """Проверяет, настроен ли Firebase"""
        return (bool(cls.API_KEY) and
                cls.API_KEY != "AIzaSyXXXXXXXXXXXX" and
                os.path.exists(cls.SERVICE_ACCOUNT_KEY_PATH))


# Настройки GitHub Releases для хранения PDF и обложек
class GitHubConfig:
    """Конфигурация GitHub Releases"""
    REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER", "NurApps")
    REPO_NAME = os.environ.get("GITHUB_REPO_NAME", "NurBooks-Releases")
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # держите в .env

    @classmethod
    def get_release_url(cls, asset_name: str) -> str:
        """Формирует URL для скачивания файла из GitHub Releases"""
        return f"https://github.com/{cls.REPO_OWNER}/{cls.REPO_NAME}/releases/latest/download/{asset_name}"

    @classmethod
    def get_api_url(cls) -> str:
        """URL API для получения информации о релизах"""
        return f"https://api.github.com/repos/{cls.REPO_OWNER}/{cls.REPO_NAME}/releases/latest"
