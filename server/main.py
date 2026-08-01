"""
NurBooks API Server — прокси между десктоп-приложением и Firebase Firestore.
"""
import os

import firebase_service as fb
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from models import (
    AnalyticsEventCreate,
    AuthorCreate,
    BookCreate,
    BookmarkCreate,
    BookUpdate,
    FavoriteCreate,
    ReadingProgressSave,
)
from rate_limit import RateLimitMiddleware

API_KEY = os.environ.get("NURBOOKS_API_KEY", "")
APP_VERSION = "1.4.0 Beta"

# Отключаем цветной логгер uvicorn (глючит на Render без TTY)
import logging  # noqa: E402

logging.getLogger("uvicorn").handlers.clear()  # noqa: E402
logging.getLogger("uvicorn.access").handlers.clear()  # noqa: E402


def require_api_key(
    api_key: str = Query(""),
    x_api_key: str = Header(""),
) -> None:
    """Проверяет API-ключ: заголовок X-API-Key или query-параметр api_key (legacy)."""
    key = (x_api_key or api_key).strip()
    if API_KEY and key != API_KEY:
        raise HTTPException(403, "Invalid API key")


app = FastAPI(
    title="NurBooks API",
    version=APP_VERSION,
    description="Электронная исламская библиотека от NurApps.",
    dependencies=[Depends(require_api_key)],
)

# CORS: по умолчанию закрыт, разрешённые origin'ы задаются переменной окружения.
_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limit: настраивается через RATE_LIMIT_MAX / RATE_LIMIT_WINDOW.
app.add_middleware(
    RateLimitMiddleware,
    max_requests=int(os.environ.get("RATE_LIMIT_MAX", "120")),
    window_seconds=int(os.environ.get("RATE_LIMIT_WINDOW", "60")),
    exempt_paths=["/health"],
)


@app.get("/")
def root():
    return {"name": "NurBooks API", "version": APP_VERSION, "status": "ok"}


def require_firebase():
    if not fb.is_ready():
        raise HTTPException(503, f"Firebase not ready: {fb.init_error()}")


def resolve_uid(authorization: str = Header("")) -> str:
    """Возвращает uid из Bearer-токена, либо 'public' для анонимных запросов.

    Старые данные без userId остаются доступными под скоупом 'public'.
    """
    token = authorization.replace("Bearer ", "").strip()
    if token:
        uid = fb.verify_token(token)
        if uid:
            return uid
    return "public"


# ============ Books ============


@app.get("/books")
def get_all_books():
    require_firebase()
    return fb.all_books()


@app.get("/books/search")
def search_books(q: str = Query("")):
    require_firebase()
    if not q:
        return []
    return fb.search_books(q)


@app.get("/books/by-pdf")
def get_book_by_pdf(path: str = ""):
    require_firebase()
    book = fb.get_book_by_pdf(path)
    if not book:
        raise HTTPException(404, "Book not found")
    return book


@app.get("/books/{book_id}")
def get_book(book_id: int):
    require_firebase()
    book = fb.book_doc(book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    return book


@app.post("/books")
def create_book(data: BookCreate):
    require_firebase()
    result = fb.add_book(data.model_dump())
    if result == "id_exists":
        raise HTTPException(409, "Book with this ID already exists")
    return {"status": result}


@app.put("/books/{book_id}")
def update_book(book_id: int, data: BookUpdate):
    require_firebase()
    existing = fb.book_doc(book_id)
    if not existing:
        raise HTTPException(404, "Book not found")
    merged = {**existing, **{k: v for k, v in data.model_dump().items() if v is not None}}
    fb.update_book(book_id, merged)
    return {"status": "success"}


@app.delete("/books/{book_id}")
def delete_book(book_id: int):
    require_firebase()
    fb.delete_book(book_id)
    return {"status": "success"}


@app.delete("/books")
def clear_books():
    require_firebase()
    fb.clear_books()
    return {"status": "success"}


@app.post("/books/{book_id}/view")
def increment_view(book_id: int):
    require_firebase()
    fb.increment_view(book_id)
    fb.log_event("view", book_id)
    return {"status": "success"}


@app.post("/books/{book_id}/download")
def increment_download(book_id: int):
    require_firebase()
    fb.increment_download(book_id)
    fb.log_event("download", book_id)
    return {"status": "success"}


@app.get("/books/{book_id}/statistics")
def get_statistics(book_id: int):
    require_firebase()
    return fb.book_statistics(book_id)


# ============ Authors ============


@app.get("/authors")
def get_all_authors():
    require_firebase()
    return fb.all_authors()


@app.post("/authors")
def create_author(data: AuthorCreate):
    require_firebase()
    result = fb.add_author(data.model_dump())
    if result == "id_exists":
        raise HTTPException(409, "Author with this ID already exists")
    return {"status": result}


@app.put("/authors")
def save_authors(authors: list[dict] = Body(...)):
    require_firebase()
    fb.save_authors(authors)
    return {"status": "success"}


# ============ Bookmarks ============


@app.post("/bookmarks")
def create_bookmark(data: BookmarkCreate, authorization: str = Header("")):
    require_firebase()
    payload = data.model_dump()
    payload["userId"] = resolve_uid(authorization)
    bm = fb.add_bookmark(payload)
    return bm


@app.get("/bookmarks")
def get_bookmarks(book_id: int = 0, authorization: str = Header("")):
    require_firebase()
    if book_id:
        return fb.get_bookmarks_by_book(book_id, resolve_uid(authorization))
    return []


@app.get("/bookmarks/with-books")
def get_bookmarks_with_books(authorization: str = Header("")):
    require_firebase()
    return fb.all_bookmarks_with_books(resolve_uid(authorization))


@app.delete("/bookmarks/{bookmark_id}")
def delete_bookmark(bookmark_id: str, authorization: str = Header("")):
    require_firebase()
    fb.delete_bookmark(bookmark_id, resolve_uid(authorization))
    return {"status": "success"}


# ============ Favorites ============


@app.get("/favorites")
def get_favorites(authorization: str = Header("")):
    require_firebase()
    return {"favorites": fb.all_favorites(resolve_uid(authorization))}


@app.post("/favorites")
def create_favorite(data: FavoriteCreate, authorization: str = Header("")):
    require_firebase()
    fb.add_favorite(resolve_uid(authorization), data.bookId)
    return {"status": "success"}


@app.delete("/favorites/{book_id}")
def delete_favorite(book_id: int, authorization: str = Header("")):
    require_firebase()
    fb.remove_favorite(resolve_uid(authorization), book_id)
    return {"status": "success"}


# ============ Reading Progress ============


@app.put("/reading-progress/{book_id}")
def save_progress(book_id: int, data: ReadingProgressSave, authorization: str = Header("")):
    require_firebase()
    fb.save_reading_progress(book_id, data.page, resolve_uid(authorization))
    return {"status": "success"}


@app.get("/reading-progress/{book_id}")
def get_progress(book_id: int, authorization: str = Header("")):
    require_firebase()
    page = fb.get_reading_progress(book_id, resolve_uid(authorization))
    return {"page": page} if page else {"page": None}


@app.get("/reading-progress")
def get_all_progress(authorization: str = Header("")):
    require_firebase()
    return fb.all_reading_progress(resolve_uid(authorization))


# ============ Analytics ============


@app.post("/analytics/events")
def log_event(data: AnalyticsEventCreate, authorization: str = Header("")):
    require_firebase()
    fb.log_event(data.eventType, data.bookId, data.metadata, resolve_uid(authorization))
    return {"status": "success"}


@app.get("/analytics/history")
def get_history(authorization: str = Header("")):
    require_firebase()
    return fb.get_reading_history(resolve_uid(authorization))


@app.get("/analytics/books/{book_id}")
def get_analytics(book_id: int):
    require_firebase()
    return fb.get_book_analytics(book_id)


# ============ Health ============


@app.get("/health")
def health():
    return {
        "status": "ok" if fb.is_ready() else "error",
        "firebase": "ready" if fb.is_ready() else fb.init_error(),
        "version": APP_VERSION,
    }
