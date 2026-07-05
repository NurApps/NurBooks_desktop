"""
HTTP-клиент к NurBooks API Server (Firebase через сервер).
"""
from typing import Optional, List, Dict, Any
import urllib.request
import urllib.error
import json
from src.core.models import Book, Bookmark
from src.core.logger import get_logger
from src.config import API_BASE_URL, API_KEY as CONFIG_API_KEY

logger = get_logger(__name__)

API_BASE = API_BASE_URL.rstrip("/")
API_KEY = CONFIG_API_KEY


def _url(path: str) -> str:
    return f"{API_BASE}{path}"


def _get(path: str) -> Optional[Any]:
    try:
        url = _url(path)
        if API_KEY:
            sep = "&" if "?" in path else "?"
            url += f"{sep}api_key={API_KEY}"
        resp = urllib.request.urlopen(url, timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        logger.error(f"HTTP {e.code} GET {path}: {e.read().decode()}")
        return None
    except Exception as e:
        logger.error(f"GET {path} error: {e}")
        return None


def _post(path: str, data: dict = None) -> Optional[Any]:
    try:
        url = _url(path)
        if API_KEY:
            sep = "&" if "?" in path else "?"
            url += f"{sep}api_key={API_KEY}"
        body = json.dumps(data).encode() if data else b"{}"
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP {e.code} POST {path}: {e.read().decode()}")
        return None
    except Exception as e:
        logger.error(f"POST {path} error: {e}")
        return None


def _put(path: str, data: dict = None) -> Optional[Any]:
    try:
        url = _url(path)
        if API_KEY:
            sep = "&" if "?" in path else "?"
            url += f"{sep}api_key={API_KEY}"
        body = json.dumps(data).encode() if data else b"{}"
        req = urllib.request.Request(url, data=body, method="PUT",
                                     headers={"Content-Type": "application/json"})
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
        if API_KEY:
            sep = "&" if "?" in path else "?"
            url += f"{sep}api_key={API_KEY}"
        req = urllib.request.Request(url, method="DELETE")
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

    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        data = _get(f"/books/{book_id}")
        return self._dict_to_book(data) if data else None

    def get_book_by_pdf(self, pdf_path: str) -> Optional[Book]:
        import urllib.parse
        data = _get(f"/books/by-pdf?path={urllib.parse.quote(pdf_path)}")
        return self._dict_to_book(data) if data else None

    def get_all_books(self) -> List[Book]:
        data = _get("/books")
        return [self._dict_to_book(b) for b in data] if data else []

    def search_books(self, query: str) -> List[Book]:
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

    def get_book_statistics(self, book_id: int) -> Dict[str, Any]:
        data = _get(f"/books/{book_id}/statistics")
        return data or {"view_count": 0, "download_count": 0, "view_to_download_ratio": 0}

    def log_analytics_event(self, event_type: str, book_id: int, metadata: Dict[str, Any] = None) -> bool:
        result = _post("/analytics/events", {
            "eventType": event_type,
            "bookId": book_id,
            "metadata": metadata or {},
        })
        return result is not None

    def get_book_analytics(self, book_id: int) -> Dict[str, Any]:
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

    def get_bookmark_by_id(self, bookmark_id) -> Optional[Bookmark]:
        return None  # not exposed via API

    def get_bookmarks_by_book(self, book_id: int) -> List[Bookmark]:
        data = _get(f"/bookmarks?book_id={book_id}")
        if not data:
            return []
        return [Bookmark(id=b.get("id"), book_id=b.get("bookId"), page_number=b.get("page"), timestamp=b.get("timestamp")) for b in data]

    def delete_bookmark(self, bookmark_id) -> bool:
        return _delete(f"/bookmarks/{bookmark_id}")

    def get_all_bookmarks_with_books(self) -> List:
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

    # ---- Authors ----

    def get_all_authors(self) -> List[dict]:
        data = _get("/authors")
        return data or []

    def add_author(self, author_data: dict) -> str:
        result = _post("/authors", author_data)
        if result is None:
            return "error"
        if isinstance(result, dict) and result.get("status") == "id_exists":
            return "id_exists"
        return "success"

    def save_authors(self, authors_data: List[dict]) -> bool:
        result = _put("/authors", authors_data)
        return result is not None

    # ---- Auth (no-op via API) ----

    def sign_in_anonymous(self) -> Optional[str]:
        return None

    def sign_in_with_email(self, email: str, password: str) -> Optional[str]:
        return None

    def sign_out(self) -> bool:
        return True

    def get_current_user(self) -> Optional[dict]:
        return None


firebase_client = FirebaseClient()
