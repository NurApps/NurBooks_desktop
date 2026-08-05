import json
import os
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


def init_error() -> str | None:
    return _init_error


def verify_token(id_token: str) -> str | None:
    """Проверяет Firebase ID-токен и возвращает uid пользователя (или None)."""
    if not id_token:
        return None
    try:
        from firebase_admin import auth as firebase_auth
        decoded = firebase_auth.verify_id_token(id_token)
        return decoded.get("uid")
    except Exception as e:
        print(f"[Firebase] Token verification failed: {e}", flush=True)
        return None


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


def get_book_by_pdf(pdf_path: str) -> dict | None:
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
        "userId": data.get("userId", "public"),
    }
    doc_ref.set(bookmark)
    return bookmark


def get_bookmarks_by_book(book_id: int, uid: str = "public") -> list:
    docs = _firestore.collection("bookmarks").where("bookId", "==", book_id).order_by("page").stream()
    return [
        doc.to_dict() for doc in docs
        if doc.to_dict().get("userId", "public") == uid
    ]


def delete_bookmark(bookmark_id: str, uid: str = "public"):
    doc = _firestore.collection("bookmarks").document(str(bookmark_id)).get()
    if doc.exists and doc.to_dict().get("userId", "public") == uid:
        doc.reference.delete()


def all_bookmarks_with_books(uid: str = "public") -> list:
    result = []
    docs = _firestore.collection("bookmarks").order_by("timestamp", direction="DESCENDING").stream()
    for doc in docs:
        bm = doc.to_dict()
        if bm.get("userId", "public") != uid:
            continue
        book = book_doc(bm.get("bookId"))
        if book:
            result.append({"bookmark": bm, "book": book})
    return result


# ---- Favorites ----

def add_favorite(uid: str, book_id: int):
    _firestore.collection("favorites").document(f"{uid}_{book_id}").set({
        "bookId": book_id,
        "userId": uid,
        "timestamp": datetime.now().isoformat(),
    })


def remove_favorite(uid: str, book_id: int):
    doc = _firestore.collection("favorites").document(f"{uid}_{book_id}").get()
    if doc.exists and doc.to_dict().get("userId") == uid:
        doc.reference.delete()


def all_favorites(uid: str) -> list:
    docs = _firestore.collection("favorites").where("userId", "==", uid).order_by("timestamp").stream()
    return [doc.to_dict().get("bookId") for doc in docs]


# ---- Wishlist ----

def add_wishlist(uid: str, book_id: int):
    _firestore.collection("wishlist").document(f"{uid}_{book_id}").set({
        "bookId": book_id,
        "userId": uid,
        "timestamp": datetime.now().isoformat(),
    })


def remove_wishlist(uid: str, book_id: int):
    doc = _firestore.collection("wishlist").document(f"{uid}_{book_id}").get()
    if doc.exists and doc.to_dict().get("userId") == uid:
        doc.reference.delete()


def all_wishlist(uid: str) -> list:
    docs = _firestore.collection("wishlist").where("userId", "==", uid).order_by("timestamp").stream()
    return [doc.to_dict().get("bookId") for doc in docs]


# ---- Ratings & Reviews ----

def upsert_rating(uid: str, book_id: int, rating: int, review: str | None = None, nickname: str | None = None):
    doc_ref = _firestore.collection("ratings").document(f"{book_id}_{uid}")
    data = {
        "bookId": book_id,
        "userId": uid,
        "rating": max(1, min(5, int(rating))),
        "updatedAt": datetime.now().isoformat(),
    }
    if nickname:
        data["nickname"] = nickname
    if review is not None:
        data["review"] = review.strip() if isinstance(review, str) else review
    if not doc_ref.get().exists:
        data["createdAt"] = datetime.now().isoformat()
    doc_ref.set(data, merge=True)


def delete_rating(uid: str, book_id: int):
    doc = _firestore.collection("ratings").document(f"{book_id}_{uid}").get()
    if doc.exists and doc.to_dict().get("userId") == uid:
        doc.reference.delete()


def book_ratings(book_id: int, uid: str = "public") -> dict:
    """Рейтинг книги: среднее, распределение, отзывы и оценка текущего пользователя."""
    reviews = []
    total = 0
    count = 0
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    user_rating = None
    docs = _firestore.collection("ratings").where("bookId", "==", book_id).stream()
    for doc in docs:
        d = doc.to_dict()
        r = d.get("rating", 0)
        total += r
        count += 1
        distribution[r] = distribution.get(r, 0) + 1
        if d.get("userId") == uid:
            user_rating = r
        if d.get("review"):
            reviews.append({
                "nickname": d.get("nickname", "Читатель"),
                "rating": r,
                "review": d.get("review"),
                "updatedAt": d.get("updatedAt", ""),
            })
    reviews.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)
    return {
        "average": round(total / count, 2) if count else 0,
        "count": count,
        "distribution": {str(k): distribution.get(k, 0) for k in (1, 2, 3, 4, 5)},
        "userRating": user_rating,
        "reviews": reviews,
    }


# ---- Users ----

def upsert_user(uid: str, nickname: str):
    """Создаёт или обновляет профиль пользователя (ник)."""
    _firestore.collection("users").document(uid).set({
        "userId": uid,
        "nickname": nickname,
        "updatedAt": datetime.now().isoformat(),
    })


# ---- Reading Progress ----

def save_reading_progress(book_id: int, page: int, uid: str = "public"):
    _firestore.collection("reading_progress").document(f"{uid}_{book_id}").set({
        "bookId": book_id,
        "page": page,
        "userId": uid,
        "timestamp": datetime.now().isoformat(),
    })


def get_reading_progress(book_id: int, uid: str = "public") -> int | None:
    doc = _firestore.collection("reading_progress").document(f"{uid}_{book_id}").get()
    if doc.exists:
        return doc.to_dict().get("page")
    # Обратная совместимость: данные без userId
    legacy = _firestore.collection("reading_progress").document(str(book_id)).get()
    return legacy.to_dict().get("page") if legacy.exists else None


def all_reading_progress(uid: str = "public") -> dict:
    result = {}
    docs = _firestore.collection("reading_progress").order_by("timestamp", direction="DESCENDING").stream()
    for doc in docs:
        d = doc.to_dict()
        if d.get("userId", "public") != uid:
            continue
        result[d["bookId"]] = d.get("page", 0)
    return result


# ---- Analytics Events ----

def log_event(event_type: str, book_id: int, metadata: dict = None, uid: str = "public"):
    event = {
        "eventType": event_type,
        "bookId": book_id,
        "userId": uid,
        "timestamp": datetime.now().isoformat(),
    }
    if metadata:
        event.update(metadata)
    _firestore.collection("analytics_events").add(event)


def get_reading_history(uid: str, limit: int = 50) -> list:
    """Последние события чтения пользователя (с данными книги)."""
    result = []
    docs = _firestore.collection("analytics_events").order_by("timestamp", direction="DESCENDING").limit(limit).stream()
    for doc in docs:
        d = doc.to_dict()
        if d.get("userId", "public") != uid:
            continue
        if d.get("eventType") not in ("read", "read_open"):
            continue
        book = book_doc(d.get("bookId"))
        if not book:
            continue
        result.append({
            "eventType": d.get("eventType"),
            "bookId": d.get("bookId"),
            "timestamp": d.get("timestamp"),
            "page": d.get("page", 0),
            "durationSeconds": d.get("durationSeconds", 0),
            "book": book,
        })
    return result


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


# ---- Reading statistics (личная статистика) ----

def _ts_to_date(ts: str):
    """ISO-строка → дата (YYYY-MM-DD). Терпимо к отсутствию/порче."""
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return None


def reading_stats(uid: str, days: int = 30) -> dict:
    """Статистика чтения пользователя за последние N дней."""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    per_day = {}
    books_read = set()
    docs = _firestore.collection("analytics_events").where("userId", "==", uid).stream()
    for doc in docs:
        d = doc.to_dict()
        if d.get("eventType") != "read":
            continue
        ts = d.get("timestamp", "")
        if ts < cutoff:
            continue
        date = _ts_to_date(ts)
        if not date:
            continue
        pages = int(d.get("page", 0) or 0)
        minutes = round(int(d.get("durationSeconds", 0) or 0) / 60)
        day = per_day.setdefault(date, {"date": date, "pages": 0, "minutes": 0, "sessions": 0})
        day["pages"] += pages
        day["minutes"] += minutes
        day["sessions"] += 1
        if d.get("bookId"):
            books_read.add(d.get("bookId"))
    result = {
        "days": sorted(per_day.values(), key=lambda x: x["date"]),
        "totalPages": sum(x["pages"] for x in per_day.values()),
        "totalMinutes": sum(x["minutes"] for x in per_day.values()),
        "totalSessions": sum(x["sessions"] for x in per_day.values()),
        "booksRead": len(books_read),
    }
    # Дополняем днями без чтения в интервале (чтобы график был ровным)
    result["days"] = _fill_days(result["days"], days)
    return result


def _fill_days(days: list, span: int) -> list:
    from datetime import timedelta
    by_date = {d["date"]: d for d in days}
    filled = []
    today = datetime.now()
    for i in range(span - 1, -1, -1):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        filled.append(by_date.get(date, {"date": date, "pages": 0, "minutes": 0, "sessions": 0}))
    return filled


# ---- Leaderboard ----

def leaderboard(days: int = 7, limit: int = 10) -> list:
    """Топ читателей по времени чтения за последние N дней."""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    by_user = {}
    docs = _firestore.collection("analytics_events").where("timestamp", ">=", cutoff).stream()
    for doc in docs:
        d = doc.to_dict()
        if d.get("eventType") != "read":
            continue
        uid = d.get("userId", "public")
        if uid == "public":
            continue
        entry = by_user.setdefault(uid, {"minutes": 0, "pages": 0, "sessions": 0})
        entry["minutes"] += round(int(d.get("durationSeconds", 0) or 0) / 60)
        entry["pages"] += int(d.get("page", 0) or 0)
        entry["sessions"] += 1
    ranked = sorted(by_user.items(), key=lambda kv: (kv[1]["minutes"], kv[1]["pages"]), reverse=True)
    result = []
    for uid, data in ranked[:limit]:
        user_doc = _firestore.collection("users").document(str(uid)).get()
        nickname = user_doc.to_dict().get("nickname") if user_doc.exists else None
        result.append({
            "uid": uid,
            "nickname": nickname or _default_nickname(uid),
            "minutes": data["minutes"],
            "pages": data["pages"],
            "sessions": data["sessions"],
        })
    return result


def _default_nickname(uid: str) -> str:
    return f"Читатель-{str(uid)[:6]}"


# ---- Libraries (общие библиотеки) ----

def _library_to_dict(doc) -> dict | None:
    data = doc.to_dict()
    if not data:
        return None
    data["id"] = doc.id
    data["memberCount"] = len(data.get("memberUids", [])) + 1  # + владелец
    data["bookCount"] = len(data.get("bookIds", []))
    return data


def create_library(uid: str, title: str, description: str, visibility: str, book_ids: list) -> dict:
    doc_ref = _firestore.collection("libraries").document()
    lib = {
        "ownerUid": uid,
        "ownerNickname": _owner_nickname(uid),
        "title": (title or "Библиотека").strip()[:120],
        "description": (description or "").strip()[:500],
        "visibility": visibility if visibility in ("public", "private") else "public",
        "bookIds": [int(b) for b in (book_ids or [])],
        "memberUids": [],
        "inviteCode": _generate_invite_code(),
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
    }
    doc_ref.set(lib)
    return _library_to_dict(doc_ref)


def _owner_nickname(uid: str) -> str:
    doc = _firestore.collection("users").document(str(uid)).get()
    if doc.exists:
        return doc.to_dict().get("nickname") or _default_nickname(uid)
    return _default_nickname(uid)


def _generate_invite_code(length: int = 6) -> str:
    import random
    import string
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choice(alphabet) for _ in range(length))
        exists = False
        for d in _firestore.collection("libraries").where("inviteCode", "==", code).limit(1).stream():
            exists = True
            break
        if not exists:
            return code


def get_library(lib_id: str) -> dict | None:
    doc = _firestore.collection("libraries").document(str(lib_id)).get()
    return _library_to_dict(doc) if doc.exists else None


def list_libraries(uid: str) -> list:
    """Публичные библиотеки + свои + те, куда добавлен пользователь."""
    result = {}
    for doc in _firestore.collection("libraries").stream():
        d = doc.to_dict()
        if not d:
            continue
        if d.get("visibility") == "public" or d.get("ownerUid") == uid or uid in d.get("memberUids", []):
            result[doc.id] = _library_to_dict(doc)
    return sorted(result.values(), key=lambda x: x.get("updatedAt", ""), reverse=True)


def update_library(lib_id: str, uid: str, data: dict) -> bool:
    doc = _firestore.collection("libraries").document(str(lib_id)).get()
    if not doc.exists or doc.to_dict().get("ownerUid") != uid:
        return False
    updates = {}
    if "title" in data and data["title"] is not None:
        updates["title"] = str(data["title"]).strip()[:120]
    if "description" in data and data["description"] is not None:
        updates["description"] = str(data["description"]).strip()[:500]
    if "visibility" in data and data["visibility"] in ("public", "private"):
        updates["visibility"] = data["visibility"]
    if "bookIds" in data and data["bookIds"] is not None:
        updates["bookIds"] = [int(b) for b in data["bookIds"]]
    updates["updatedAt"] = datetime.now().isoformat()
    doc.reference.update(updates)
    return True


def delete_library(lib_id: str, uid: str) -> bool:
    doc = _firestore.collection("libraries").document(str(lib_id)).get()
    if not doc.exists or doc.to_dict().get("ownerUid") != uid:
        return False
    doc.reference.delete()
    return True


def add_book_to_library(lib_id: str, uid: str, book_id: int) -> bool:
    doc = _firestore.collection("libraries").document(str(lib_id)).get()
    if not doc.exists:
        return False
    d = doc.to_dict()
    if d.get("ownerUid") != uid:
        return False
    books = [int(b) for b in d.get("bookIds", [])]
    if book_id not in books:
        books.append(book_id)
    doc.reference.update({"bookIds": books, "updatedAt": datetime.now().isoformat()})
    return True


def remove_book_from_library(lib_id: str, uid: str, book_id: int) -> bool:
    doc = _firestore.collection("libraries").document(str(lib_id)).get()
    if not doc.exists:
        return False
    d = doc.to_dict()
    if d.get("ownerUid") != uid:
        return False
    books = [int(b) for b in d.get("bookIds", []) if int(b) != int(book_id)]
    doc.reference.update({"bookIds": books, "updatedAt": datetime.now().isoformat()})
    return True


def join_library_by_code(uid: str, invite_code: str) -> str | None:
    """Вступление в библиотеку по коду. Возвращает id библиотеки или None."""
    code = invite_code.strip().upper()
    for doc in _firestore.collection("libraries").where("inviteCode", "==", code).limit(1).stream():
        d = doc.to_dict()
        if d.get("ownerUid") == uid:
            return doc.id
        members = d.get("memberUids", [])
        if uid not in members:
            members.append(uid)
            doc.reference.update({"memberUids": members, "updatedAt": datetime.now().isoformat()})
        return doc.id
    return None


def rate_library(uid: str, lib_id: str, rating: int) -> dict:
    """Оценка библиотеки (1-5). Возвращает актуальный рейтинг библиотеки."""
    lib = _firestore.collection("libraries").document(str(lib_id)).get()
    if not lib.exists:
        return {}
    doc_ref = _firestore.collection("library_ratings").document(f"{lib_id}_{uid}")
    data = {
        "libraryId": lib_id,
        "userId": uid,
        "rating": max(1, min(5, int(rating))),
        "updatedAt": datetime.now().isoformat(),
    }
    if not doc_ref.get().exists:
        data["createdAt"] = datetime.now().isoformat()
    doc_ref.set(data, merge=True)
    return library_rating(lib_id, uid)


def remove_library_rating(uid: str, lib_id: str) -> dict:
    """Снятие оценки с библиотеки. Возвращает актуальный рейтинг библиотеки."""
    doc = _firestore.collection("library_ratings").document(f"{lib_id}_{uid}").get()
    if doc.exists and doc.to_dict().get("userId") == uid:
        doc.reference.delete()
    return library_rating(lib_id, uid)


def library_rating(lib_id: str, uid: str = "public") -> dict:
    """Рейтинг библиотеки: среднее, количество оценок и оценка текущего пользователя."""
    total = 0
    count = 0
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    user_rating = None
    docs = _firestore.collection("library_ratings").where("libraryId", "==", lib_id).stream()
    for doc in docs:
        d = doc.to_dict()
        r = d.get("rating", 0)
        total += r
        count += 1
        distribution[r] = distribution.get(r, 0) + 1
        if d.get("userId") == uid:
            user_rating = r
    return {
        "average": round(total / count, 2) if count else 0,
        "count": count,
        "distribution": distribution,
        "myRating": user_rating,
    }
