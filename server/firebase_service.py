import os
import json
from typing import Optional
from datetime import datetime

FIREBASE_PROJECT_ID = "nurbooks-3b694"
_firestore = None
_init_error = None


def _init_firebase():
    global _firestore, _init_error
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        if firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
            _firestore = firestore.client()
            return

        key_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY_PATH", "serviceAccountKey.json")
        if os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            print(f"[Firebase] Using key file: {key_path}", flush=True)
        elif os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON"):
            raw = os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"]
            cred = credentials.Certificate(json.loads(raw))
            print("[Firebase] Using FIREBASE_SERVICE_ACCOUNT_JSON env var", flush=True)
        else:
            _init_error = "No Firebase credentials (set FIREBASE_SERVICE_ACCOUNT_JSON)"
            print(f"[Firebase] ERROR: {_init_error}", flush=True)
            return

        firebase_admin.initialize_app(cred, {"projectId": FIREBASE_PROJECT_ID})
        _firestore = firestore.client()
        _init_error = None
        print("[Firebase] Initialized successfully", flush=True)
    except Exception as e:
        _init_error = str(e)
        print(f"[Firebase] Init failed: {e}", flush=True)


def is_ready() -> bool:
    return _firestore is not None


def init_error() -> Optional[str]:
    return _init_error


_init_firebase()


def book_doc(book_id: int) -> dict:
    doc = _firestore.collection("books").document(str(book_id)).get()
    return doc.to_dict() if doc.exists else None


def all_books() -> list:
    return [doc.to_dict() for doc in _firestore.collection("books").order_by("id").stream()]


def add_book(data: dict) -> str:
    bid = data.get("id")
    if _firestore.collection("books").document(str(bid)).get().exists:
        return "id_exists"
    _firestore.collection("books").document(str(bid)).set(data)
    return "success"


def update_book(book_id: int, data: dict):
    _firestore.collection("books").document(str(book_id)).set(data)


def delete_book(book_id: int):
    _firestore.collection("books").document(str(book_id)).delete()


def clear_books():
    for doc in _firestore.collection("books").stream():
        doc.reference.delete()


def search_books(query: str) -> list:
    results = []
    seen = set()
    for doc in _firestore.collection("books").where("title", ">=", query).where("title", "<=", query + "z").stream():
        d = doc.to_dict()
        if d["id"] not in seen:
            results.append(d)
            seen.add(d["id"])
    for doc in _firestore.collection("books").where("author", ">=", query).where("author", "<=", query + "z").stream():
        d = doc.to_dict()
        if d["id"] not in seen:
            results.append(d)
            seen.add(d["id"])
    return results


def get_book_by_pdf(pdf_path: str) -> Optional[dict]:
    docs = _firestore.collection("books").where("pdf", "==", pdf_path).limit(1).stream()
    for doc in docs:
        return doc.to_dict()
    return None


def increment_view(book_id: int):
    import firebase_admin
    _firestore.collection("books").document(str(book_id)).update({"viewCount": firebase_admin.firestore.Increment(1)})


def increment_download(book_id: int):
    import firebase_admin
    _firestore.collection("books").document(str(book_id)).update({"downloadCount": firebase_admin.firestore.Increment(1)})


def book_statistics(book_id: int) -> dict:
    doc = book_doc(book_id)
    if doc:
        views = doc.get("viewCount", 0)
        downloads = doc.get("downloadCount", 0)
        return {"view_count": views, "download_count": downloads, "view_to_download_ratio": downloads / views if views else 0}
    return {"view_count": 0, "download_count": 0, "view_to_download_ratio": 0}


# ---- Authors ----

def all_authors() -> list:
    return [doc.to_dict() for doc in _firestore.collection("authors").order_by("id").stream()]


def add_author(data: dict) -> str:
    aid = data.get("id")
    if _firestore.collection("authors").document(str(aid)).get().exists:
        return "id_exists"
    _firestore.collection("authors").document(str(aid)).set(data)
    return "success"


def save_authors(authors_data: list):
    batch = _firestore.batch()
    for data in authors_data:
        ref = _firestore.collection("authors").document(str(data.get("id")))
        batch.set(ref, data)
    batch.commit()


# ---- Bookmarks ----

def add_bookmark(data: dict) -> dict:
    doc_ref = _firestore.collection("bookmarks").document()
    bookmark = {
        "id": doc_ref.id,
        "bookId": data["bookId"],
        "page": data["page"],
        "timestamp": data.get("timestamp", datetime.now().isoformat()),
    }
    doc_ref.set(bookmark)
    return bookmark


def get_bookmarks_by_book(book_id: int) -> list:
    docs = _firestore.collection("bookmarks").where("bookId", "==", book_id).order_by("page").stream()
    return [doc.to_dict() for doc in docs]


def delete_bookmark(bookmark_id: str):
    _firestore.collection("bookmarks").document(str(bookmark_id)).delete()


def all_bookmarks_with_books() -> list:
    result = []
    docs = _firestore.collection("bookmarks").order_by("timestamp", direction="DESCENDING").stream()
    for doc in docs:
        bm = doc.to_dict()
        book = book_doc(bm.get("bookId"))
        if book:
            result.append({"bookmark": bm, "book": book})
    return result


# ---- Reading Progress ----

def save_reading_progress(book_id: int, page: int):
    _firestore.collection("reading_progress").document(str(book_id)).set({
        "bookId": book_id,
        "page": page,
        "timestamp": datetime.now().isoformat(),
    })


def get_reading_progress(book_id: int) -> Optional[int]:
    doc = _firestore.collection("reading_progress").document(str(book_id)).get()
    return doc.to_dict().get("page") if doc.exists else None


def all_reading_progress() -> dict:
    result = {}
    for doc in _firestore.collection("reading_progress").order_by("timestamp", direction="DESCENDING").stream():
        d = doc.to_dict()
        result[d["bookId"]] = d.get("page", 0)
    return result


# ---- Analytics Events ----

def log_event(event_type: str, book_id: int, metadata: dict = None):
    event = {"eventType": event_type, "bookId": book_id, "timestamp": datetime.now().isoformat()}
    if metadata:
        event.update(metadata)
    _firestore.collection("analytics_events").add(event)


def get_book_analytics(book_id: int) -> dict:
    views = 0
    downloads = 0
    for doc in _firestore.collection("analytics_events").where("bookId", "==", book_id).stream():
        d = doc.to_dict()
        if d.get("eventType") == "view":
            views += 1
        elif d.get("eventType") == "download":
            downloads += 1
    return {"views": views, "downloads": downloads}
