"""
HTTP-клиент к NurBooks API Server (Firebase через сервер).
Включает аутентификацию через Firebase Identity Toolkit (REST).
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any

from src.config import API_BASE_URL, DEFAULT_DATA_PATH, FirebaseConfig
from src.config import API_KEY as CONFIG_API_KEY
from src.core.logger import get_logger
from src.core.models import Book, Bookmark

logger = get_logger(__name__)

API_BASE = API_BASE_URL.rstrip("/")
API_KEY = CONFIG_API_KEY

_AUTH_TOKEN_FILE = os.path.join(DEFAULT_DATA_PATH, "auth.json")
_IDENTITY_TOOLKIT_URL = "https://identitytoolkit.googleapis.com/v1/accounts"
_SECURE_TOKEN_URL = "https://securetoken.googleapis.com/v1/token"

_NURBOOKS_EMAIL_DOMAIN = "nurbooks.local"


def _nickname_to_email(nickname: str) -> str:
    """Преобразует ник в локальную часть email (только a-z0-9_)."""
    slug = nickname.strip().lower().replace(" ", "_")
    slug = re.sub(r"[^a-z0-9_]", "", slug).strip("_")
    if not slug:
        slug = "user"
    return f"{slug}@{_NURBOOKS_EMAIL_DOMAIN}"


def _nickname_from_email(email: str | None) -> str | None:
    """Достаёт ник из email вида nick@nurbooks.local."""
    if not email:
        return None
    local = email.split("@")[0] if "@" in email else email
    return local or None


class _AuthSession:
    """Хранит ID-токен Firebase Auth и текущего пользователя (в памяти + на диске)."""

    def __init__(self):
        self._id_token: str | None = None
        self._uid: str | None = None
        self._email: str | None = None
        self._nickname: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0
        self._load()

    def _load(self):
        try:
            with open(_AUTH_TOKEN_FILE, encoding="utf-8") as f:
                data = json.load(f)
            self._id_token = data.get("id_token")
            self._uid = data.get("uid")
            self._email = data.get("email")
            self._nickname = data.get("nickname")
            self._refresh_token = data.get("refresh_token")
            self._expires_at = data.get("expires_at", 0)
        except Exception:
            pass

    def _save(self):
        try:
            os.makedirs(os.path.dirname(_AUTH_TOKEN_FILE), exist_ok=True)
            with open(_AUTH_TOKEN_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "id_token": self._id_token,
                    "uid": self._uid,
                    "email": self._email,
                    "nickname": self._nickname,
                    "refresh_token": self._refresh_token,
                    "expires_at": self._expires_at,
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Не удалось сохранить auth-сессию: {e}")

    @property
    def token(self) -> str | None:
        if self._id_token and time.time() < self._expires_at:
            return self._id_token
        return None

    @property
    def uid(self) -> str | None:
        return self._uid if self.token else None

    @property
    def email(self) -> str | None:
        return self._email

    @property
    def nickname(self) -> str | None:
        return self._nickname or _nickname_from_email(self._email)

    @property
    def refresh_token(self) -> str | None:
        return self._refresh_token

    def set(self, id_token: str, uid: str, email: str | None, expires_in: int, refresh_token: str | None = None, nickname: str | None = None):
        self._id_token = id_token
        self._uid = uid
        self._email = email
        self._nickname = nickname
        self._refresh_token = refresh_token
        self._expires_at = time.time() + expires_in
        self._save()

    def clear(self):
        self._id_token = None
        self._uid = None
        self._email = None
        self._nickname = None
        self._refresh_token = None
        self._expires_at = 0
        self._save()


auth_session = _AuthSession()


def _auth_headers() -> dict:
    headers = {}
    token = auth_session.token
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _auth_request(endpoint: str, payload: dict) -> dict | None:
    """Запрос к Firebase Identity Toolkit (signUp / signInWithPassword)."""
    url = f"{_IDENTITY_TOOLKIT_URL}:{endpoint}?key={FirebaseConfig.API_KEY}"
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            error = json.loads(body).get("error", {}).get("message", body)
        except Exception:
            error = body
        logger.error(f"Firebase Auth {endpoint} error {e.code}: {error}")
        return None
    except Exception as e:
        logger.error(f"Firebase Auth {endpoint} error: {e}")
        return None


def _api_key_headers() -> dict:
    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers


def _request_headers() -> dict:
    return {**_auth_headers(), **_api_key_headers()}


def _url(path: str) -> str:
    return f"{API_BASE}{path}"


def _get(path: str) -> Any | None:
    try:
        url = _url(path)
        req = urllib.request.Request(url, headers=_request_headers())
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        logger.error(f"HTTP {e.code} GET {path}: {e.read().decode()}")
        return None
    except Exception as e:
        logger.error(f"GET {path} error: {e}")
        return None


def _post(path: str, data: dict = None) -> Any | None:
    try:
        url = _url(path)
        body = json.dumps(data).encode() if data else b"{}"
        headers = {"Content-Type": "application/json", **_request_headers()}
        req = urllib.request.Request(url, data=body, method="POST", headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP {e.code} POST {path}: {e.read().decode()}")
        return None
    except Exception as e:
        logger.error(f"POST {path} error: {e}")
        return None


def _put(path: str, data: dict = None) -> Any | None:
    try:
        url = _url(path)
        body = json.dumps(data).encode() if data else b"{}"
        headers = {"Content-Type": "application/json", **_request_headers()}
        req = urllib.request.Request(url, data=body, method="PUT", headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP {e.code} PUT {path}: {e.read().decode()}")
        return None
    except Exception as e:
        logger.error(f"PUT {path} error: {e}")
        return None


def _delete(path: str) -> bool:
    try:
        url = _url(path)
        req = urllib.request.Request(url, method="DELETE", headers=_request_headers())
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status == 200
    except Exception as e:
        logger.error(f"DELETE {path} error: {e}")
        return False


class FirebaseClient:
    """HTTP-клиент к NurBooks API (сервер с Firebase Admin SDK)."""

    def __init__(self):
        self._initialized = self._check()

    def _check(self) -> bool:
        try:
            resp = _get("/health")
            return resp is not None and resp.get("status") == "ok"
        except Exception:
            return False

    def is_initialized(self) -> bool:
        return self._initialized

    # ---- Books ----

    def _dict_to_book(self, d: dict) -> Book:
        return Book(
            id=d.get("id", 0),
            title=d.get("title", ""),
            author=d.get("author", ""),
            category=d.get("category", ""),
            year=d.get("year", 0),
            description=d.get("description", ""),
            cover=d.get("cover", ""),
            pdf=d.get("pdf", ""),
            file_size=d.get("fileSize"),
            pages=d.get("pages"),
            copyright_protected=bool(d.get("copyrightProtected", False)),
            view_count=d.get("viewCount", 0),
            download_count=d.get("downloadCount", 0),
        )

    def get_book_by_id(self, book_id: int) -> Book | None:
        data = _get(f"/books/{book_id}")
        return self._dict_to_book(data) if data else None

    def get_book_by_pdf(self, pdf_path: str) -> Book | None:
        import urllib.parse
        data = _get(f"/books/by-pdf?path={urllib.parse.quote(pdf_path)}")
        return self._dict_to_book(data) if data else None

    def get_all_books(self) -> list[Book]:
        data = _get("/books")
        return [self._dict_to_book(b) for b in data] if data else []

    def search_books(self, query: str) -> list[Book]:
        import urllib.parse
        data = _get(f"/books/search?q={urllib.parse.quote(query)}")
        return [self._dict_to_book(b) for b in data] if data else []

    def add_book(self, book: Book) -> str:
        result = _post("/books", {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "category": book.category,
            "year": book.year,
            "description": book.description,
            "cover": book.cover,
            "pdf": book.pdf,
            "fileSize": book.file_size,
            "pages": book.pages,
            "copyrightProtected": bool(book.copyright_protected),
            "viewCount": book.view_count,
            "downloadCount": book.download_count,
        })
        if result is None:
            return "error"
        if isinstance(result, dict) and result.get("status") == "id_exists":
            return "id_exists"
        return "success"

    def update_book(self, book: Book) -> bool:
        result = _put(f"/books/{book.id}", {
            "title": book.title,
            "author": book.author,
            "category": book.category,
            "year": book.year,
            "description": book.description,
            "cover": book.cover,
            "pdf": book.pdf,
            "fileSize": book.file_size,
            "pages": book.pages,
            "copyrightProtected": bool(book.copyright_protected),
            "viewCount": book.view_count,
            "downloadCount": book.download_count,
        })
        return result is not None

    def delete_book(self, book_id: int) -> bool:
        return _delete(f"/books/{book_id}")

    def clear_books(self) -> bool:
        return _delete("/books")

    # ---- Analytics ----

    def increment_view_count(self, book_id: int) -> bool:
        result = _post(f"/books/{book_id}/view")
        return result is not None

    def increment_download_count(self, book_id: int) -> bool:
        result = _post(f"/books/{book_id}/download")
        return result is not None

    def get_book_statistics(self, book_id: int) -> dict[str, Any]:
        data = _get(f"/books/{book_id}/statistics")
        return data or {"view_count": 0, "download_count": 0, "view_to_download_ratio": 0}

    def log_analytics_event(self, event_type: str, book_id: int, metadata: dict[str, Any] = None) -> bool:
        result = _post("/analytics/events", {
            "eventType": event_type,
            "bookId": book_id,
            "metadata": metadata or {},
        })
        return result is not None

    def get_book_analytics(self, book_id: int) -> dict[str, Any]:
        data = _get(f"/analytics/books/{book_id}")
        return data or {}

    # ---- Bookmarks ----

    def add_bookmark(self, bookmark: Bookmark) -> bool:
        result = _post("/bookmarks", {
            "bookId": bookmark.book_id,
            "page": bookmark.page_number,
            "timestamp": bookmark.timestamp,
        })
        return result is not None

    def get_bookmark_by_id(self, bookmark_id) -> Bookmark | None:
        return None  # not exposed via API

    def get_bookmarks_by_book(self, book_id: int) -> list[Bookmark]:
        data = _get(f"/bookmarks?book_id={book_id}")
        if not data:
            return []
        return [Bookmark(id=b.get("id"), book_id=b.get("bookId"), page_number=b.get("page"), timestamp=b.get("timestamp")) for b in data]

    def delete_bookmark(self, bookmark_id) -> bool:
        return _delete(f"/bookmarks/{bookmark_id}")

    def get_all_bookmarks_with_books(self) -> list:
        data = _get("/bookmarks/with-books")
        if not data:
            return []
        result = []
        for item in data:
            bm = item.get("bookmark", {})
            bk = item.get("book", {})
            bookmark = Bookmark(id=bm.get("id"), book_id=bm.get("bookId"), page_number=bm.get("page"), timestamp=bm.get("timestamp"))
            book = self._dict_to_book(bk) if bk else None
            if book:
                result.append((bookmark, book))
        return result

    # ---- Reading Progress ----

    def save_reading_progress(self, book_id: int, page_number: int) -> bool:
        result = _put(f"/reading-progress/{book_id}", {"bookId": book_id, "page": page_number})
        return result is not None

    def get_reading_progress(self, book_id: int) -> int:
        data = _get(f"/reading-progress/{book_id}")
        if data and data.get("page") is not None:
            return data["page"]
        return 0

    def get_all_reading_progress(self) -> dict:
        data = _get("/reading-progress")
        return data or {}

    # ---- Favorites ----

    def get_favorites(self) -> list[str]:
        data = _get("/favorites")
        if data and data.get("favorites"):
            return [str(f) for f in data["favorites"]]
        return []

    def add_favorite(self, book_id: int) -> bool:
        result = _post("/favorites", {"bookId": book_id})
        return result is not None

    def remove_favorite(self, book_id: int) -> bool:
        return _delete(f"/favorites/{book_id}")

    # ---- Wishlist (Хочу прочитать) ----

    def get_wishlist(self) -> list[str]:
        data = _get("/wishlist")
        if data and data.get("wishlist"):
            return [str(w) for w in data["wishlist"]]
        return []

    def add_wishlist(self, book_id: int) -> bool:
        result = _post("/wishlist", {"bookId": book_id})
        return result is not None

    def remove_wishlist(self, book_id: int) -> bool:
        return _delete(f"/wishlist/{book_id}")

    # ---- Ratings & Reviews ----

    def get_book_ratings(self, book_id: int) -> dict[str, Any]:
        data = _get(f"/books/{book_id}/ratings")
        return data or {"average": 0, "count": 0, "distribution": {}, "userRating": None, "reviews": []}

    def rate_book(self, book_id: int, rating: int, review: str = "", nickname: str = "") -> dict[str, Any] | None:
        payload = {"bookId": book_id, "rating": rating}
        if review:
            payload["review"] = review
        if nickname:
            payload["nickname"] = nickname
        data = _put(f"/ratings/{book_id}", payload)
        return data or None

    def delete_rating(self, book_id: int) -> bool:
        return _delete(f"/ratings/{book_id}")

    # ---- Reading statistics ----

    def get_reading_stats(self, days: int = 30) -> dict[str, Any]:
        data = _get(f"/analytics/stats?days={days}")
        return data or {"days": [], "totalPages": 0, "totalMinutes": 0, "totalSessions": 0, "booksRead": 0}

    # ---- Leaderboard ----

    def get_leaderboard(self, days: int = 7, limit: int = 10) -> list[dict]:
        data = _get(f"/leaderboard?days={days}&limit={limit}")
        return data or []

    # ---- Libraries (общие библиотеки) ----

    def create_library(self, title: str, description: str = "", visibility: str = "public", book_ids: list = None) -> dict | None:
        data = _post("/libraries", {
            "title": title, "description": description, "visibility": visibility,
            "bookIds": book_ids or [],
        })
        return data or None

    def get_libraries(self) -> list[dict]:
        data = _get("/libraries")
        return data or []

    def get_library(self, lib_id: str) -> dict | None:
        return _get(f"/libraries/{lib_id}")

    def update_library(self, lib_id: str, **fields) -> bool:
        result = _put(f"/libraries/{lib_id}", {k: v for k, v in fields.items() if v is not None})
        return result is not None

    def delete_library(self, lib_id: str) -> bool:
        return _delete(f"/libraries/{lib_id}")

    def join_library(self, lib_id: str, invite_code: str) -> bool:
        result = _post(f"/libraries/{lib_id}/join", {"inviteCode": invite_code})
        return result is not None

    def add_book_to_library(self, lib_id: str, book_id: int) -> bool:
        result = _post(f"/libraries/{lib_id}/books", {"bookId": book_id})
        return result is not None

    def remove_book_from_library(self, lib_id: str, book_id: int) -> bool:
        return _delete(f"/libraries/{lib_id}/books/{book_id}")

    def get_library_rating(self, lib_id: str) -> dict:
        data = _get(f"/libraries/{lib_id}/rating")
        return data or {}

    def rate_library(self, lib_id: str, rating: int) -> dict:
        data = _put(f"/libraries/{lib_id}/rating", {"rating": rating})
        return data or {}

    def remove_library_rating(self, lib_id: str) -> dict:
        data = _delete(f"/libraries/{lib_id}/rating")
        return data or {}

    # ---- Reading History ----

    def get_reading_history(self, limit: int = 50) -> list[dict]:
        data = _get(f"/analytics/history?limit={limit}")
        return data or []

    # ---- Authors ----

    def get_all_authors(self) -> list[dict]:
        data = _get("/authors")
        return data or []

    def add_author(self, author_data: dict) -> str:
        result = _post("/authors", author_data)
        if result is None:
            return "error"
        if isinstance(result, dict) and result.get("status") == "id_exists":
            return "id_exists"
        return "success"

    def save_authors(self, authors_data: list[dict]) -> bool:
        result = _put("/authors", authors_data)
        return result is not None

    # ---- Auth (Firebase Identity Toolkit через REST) ----

    def sign_in_anonymous(self) -> str | None:
        """Анонимный вход. Возвращает uid или None."""
        data = _auth_request("signUp", {"returnSecureToken": True})
        if not data or not data.get("idToken"):
            return None
        auth_session.set(
            id_token=data["idToken"],
            uid=data["localId"],
            email=None,
            expires_in=int(data.get("expiresIn", 3600)),
            refresh_token=data.get("refreshToken"),
        )
        logger.info(f"Анонимный вход: uid={auth_session.uid}")
        return auth_session.uid

    def sign_in_with_email(self, email: str, password: str) -> str | None:
        """Вход по email/паролю. Возвращает uid или None."""
        data = _auth_request("signInWithPassword", {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        })
        if not data or not data.get("idToken"):
            return None
        auth_session.set(
            id_token=data["idToken"],
            uid=data["localId"],
            email=data.get("email", email),
            expires_in=int(data.get("expiresIn", 3600)),
            refresh_token=data.get("refreshToken"),
            nickname=_nickname_from_email(data.get("email", email)),
        )
        logger.info(f"Вход по email: uid={auth_session.uid}")
        return auth_session.uid

    def sign_in_with_nickname(self, nickname: str, password: str) -> str | None:
        """Вход по нику и паролю (как по email с локальным доменом)."""
        email = _nickname_to_email(nickname)
        data = _auth_request("signInWithPassword", {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        })
        if not data or not data.get("idToken"):
            return None
        auth_session.set(
            id_token=data["idToken"],
            uid=data["localId"],
            email=data.get("email", email),
            expires_in=int(data.get("expiresIn", 3600)),
            refresh_token=data.get("refreshToken"),
            nickname=_nickname_from_email(data.get("email", email)) or nickname.strip(),
        )
        logger.info(f"Вход по нику: uid={auth_session.uid}")
        return auth_session.uid

    def register_with_nickname(self, nickname: str, password: str) -> str | None:
        """Регистрация по нику и паролю (сохраняет профиль на сервере)."""
        email = _nickname_to_email(nickname)
        if auth_session.uid:
            data = _auth_request("update", {
                "idToken": auth_session.token or "",
                "email": email,
                "returnSecureToken": True,
            })
        else:
            data = _auth_request("signUp", {
                "email": email,
                "password": password,
                "returnSecureToken": True,
            })
        if not data or not data.get("idToken"):
            return None
        self._finalize_auth(data, email)
        self._save_user_profile(nickname.strip())
        logger.info(f"Регистрация: uid={auth_session.uid}")
        return auth_session.uid

    def _finalize_auth(self, data: dict, email: str):
        auth_session.set(
            id_token=data["idToken"],
            uid=data["localId"],
            email=data.get("email", email),
            expires_in=int(data.get("expiresIn", 3600)),
            refresh_token=data.get("refreshToken"),
            nickname=_nickname_from_email(data.get("email", email)),
        )

    def _save_user_profile(self, nickname: str):
        result = _post("/auth/register", {"nickname": nickname})
        if result is None:
            logger.warning("Не удалось сохранить профиль пользователя на сервере")

    def refresh_session(self) -> str | None:
        """Обновляет ID-токен через refreshToken (сохраняет того же пользователя)."""
        refresh = auth_session.refresh_token
        if not refresh:
            return None
        url = f"{_SECURE_TOKEN_URL}?key={FirebaseConfig.API_KEY}"
        payload = {"grant_type": "refresh_token", "refresh_token": refresh}
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            auth_session.set(
                id_token=data["id_token"],
                uid=data["user_id"],
                email=auth_session.email,
                expires_in=int(data.get("expires_in", 3600)),
                refresh_token=refresh,
            )
            logger.info(f"Сессия обновлена: uid={auth_session.uid}")
            return auth_session.uid
        except Exception as e:
            logger.warning(f"Не удалось обновить сессию: {e}")
            return None

    def sign_out(self) -> bool:
        auth_session.clear()
        logger.info("Выход из аккаунта")
        return True

    def get_current_user(self) -> dict | None:
        if auth_session.token:
            return {"uid": auth_session.uid, "email": auth_session.email, "nickname": auth_session.nickname}
        # Токен мог истечь — но сессия ещё есть, её можно обновить через refresh_token.
        if auth_session.refresh_token and auth_session._uid:
            return {"uid": auth_session._uid, "email": auth_session._email, "nickname": auth_session.nickname}
        return None


firebase_client = FirebaseClient()
