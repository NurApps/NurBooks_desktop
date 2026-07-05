"""
NurBooks API Server — прокси между десктоп-приложением и Firebase Firestore.
"""
import os
from fastapi import FastAPI, HTTPException, Query
from models import BookCreate, BookUpdate, AuthorCreate, BookmarkCreate, ReadingProgressSave, AnalyticsEventCreate
import firebase_service as fb

API_KEY = os.environ.get("NURBOOKS_API_KEY", "")

app = FastAPI(title="NurBooks API", version="1.3.5 Beta", description="Электронная исламская библиотека от NurApps.")


def verify_key(key: str):
    if API_KEY and key != API_KEY:
        raise HTTPException(403, "Invalid API key")


# ============ Books ============


@app.get("/books")
def get_all_books(api_key: str = ""):
    verify_key(api_key)
    return fb.all_books()


@app.get("/books/search")
def search_books(q: str = Query(""), api_key: str = ""):
    verify_key(api_key)
    if not q:
        return []
    return fb.search_books(q)


@app.get("/books/by-pdf")
def get_book_by_pdf(path: str = "", api_key: str = ""):
    verify_key(api_key)
    book = fb.get_book_by_pdf(path)
    if not book:
        raise HTTPException(404, "Book not found")
    return book


@app.get("/books/{book_id}")
def get_book(book_id: int, api_key: str = ""):
    verify_key(api_key)
    book = fb.book_doc(book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    return book


@app.post("/books")
def create_book(data: BookCreate, api_key: str = ""):
    verify_key(api_key)
    result = fb.add_book(data.dict())
    if result == "id_exists":
        raise HTTPException(409, "Book with this ID already exists")
    return {"status": result}


@app.put("/books/{book_id}")
def update_book(book_id: int, data: BookUpdate, api_key: str = ""):
    verify_key(api_key)
    existing = fb.book_doc(book_id)
    if not existing:
        raise HTTPException(404, "Book not found")
    merged = {**existing, **{k: v for k, v in data.dict().items() if v is not None}}
    fb.update_book(book_id, merged)
    return {"status": "success"}


@app.delete("/books/{book_id}")
def delete_book(book_id: int, api_key: str = ""):
    verify_key(api_key)
    fb.delete_book(book_id)
    return {"status": "success"}


@app.delete("/books")
def clear_books(api_key: str = ""):
    verify_key(api_key)
    fb.clear_books()
    return {"status": "success"}


@app.post("/books/{book_id}/view")
def increment_view(book_id: int, api_key: str = ""):
    verify_key(api_key)
    fb.increment_view(book_id)
    fb.log_event("view", book_id)
    return {"status": "success"}


@app.post("/books/{book_id}/download")
def increment_download(book_id: int, api_key: str = ""):
    verify_key(api_key)
    fb.increment_download(book_id)
    fb.log_event("download", book_id)
    return {"status": "success"}


@app.get("/books/{book_id}/statistics")
def get_statistics(book_id: int, api_key: str = ""):
    verify_key(api_key)
    return fb.book_statistics(book_id)


# ============ Authors ============


@app.get("/authors")
def get_all_authors(api_key: str = ""):
    verify_key(api_key)
    return fb.all_authors()


@app.post("/authors")
def create_author(data: AuthorCreate, api_key: str = ""):
    verify_key(api_key)
    result = fb.add_author(data.dict())
    if result == "id_exists":
        raise HTTPException(409, "Author with this ID already exists")
    return {"status": result}


@app.put("/authors")
def save_authors(authors: list, api_key: str = ""):
    verify_key(api_key)
    fb.save_authors(authors)
    return {"status": "success"}


# ============ Bookmarks ============


@app.post("/bookmarks")
def create_bookmark(data: BookmarkCreate, api_key: str = ""):
    verify_key(api_key)
    bm = fb.add_bookmark(data.dict())
    return bm


@app.get("/bookmarks")
def get_bookmarks(book_id: int = 0, api_key: str = ""):
    verify_key(api_key)
    if book_id:
        return fb.get_bookmarks_by_book(book_id)
    return []


@app.get("/bookmarks/with-books")
def get_bookmarks_with_books(api_key: str = ""):
    verify_key(api_key)
    return fb.all_bookmarks_with_books()


@app.delete("/bookmarks/{bookmark_id}")
def delete_bookmark(bookmark_id: str, api_key: str = ""):
    verify_key(api_key)
    fb.delete_bookmark(bookmark_id)
    return {"status": "success"}


# ============ Reading Progress ============


@app.put("/reading-progress/{book_id}")
def save_progress(book_id: int, data: ReadingProgressSave, api_key: str = ""):
    verify_key(api_key)
    fb.save_reading_progress(book_id, data.page)
    return {"status": "success"}


@app.get("/reading-progress/{book_id}")
def get_progress(book_id: int, api_key: str = ""):
    verify_key(api_key)
    page = fb.get_reading_progress(book_id)
    return {"page": page} if page else {"page": None}


@app.get("/reading-progress")
def get_all_progress(api_key: str = ""):
    verify_key(api_key)
    return fb.all_reading_progress()


# ============ Analytics ============


@app.post("/analytics/events")
def log_event(data: AnalyticsEventCreate, api_key: str = ""):
    verify_key(api_key)
    fb.log_event(data.eventType, data.bookId, data.metadata)
    return {"status": "success"}


@app.get("/analytics/books/{book_id}")
def get_analytics(book_id: int, api_key: str = ""):
    verify_key(api_key)
    return fb.get_book_analytics(book_id)


# ============ Health ============


@app.get("/health")
def health():
    return {"status": "ok"}
