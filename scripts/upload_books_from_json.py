"""
Загрузка всех книг из books_export.json в Firestore.

Использование:
1. Убедись что serviceAccountKey.json в корне проекта
2. Убедись что books_export.json создан (запусти export_sqlite_to_json.py)
3. python scripts/upload_books_from_json.py
"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath('.'))


def load_and_upload():
    """Загружает книги из JSON и создаёт документы в Firestore"""

    print("=" * 60)
    print("JSON -> Firestore Upload")
    print("=" * 60)
    print()

    # Проверяем файлы
    if not os.path.exists('serviceAccountKey.json'):
        from src.config import BASE_PATH
        sa_path = os.path.join(BASE_PATH, 'serviceAccountKey.json')
        if not os.path.exists(sa_path):
            print("[ERR] serviceAccountKey.json не найден!")
            return
        sa_path = 'serviceAccountKey.json'
    else:
        sa_path = 'serviceAccountKey.json'

    if not os.path.exists('books_export.json'):
        print("[ERR] books_export.json не найден!")
        print("Сначала запусти: python export_sqlite_to_json.py")
        return

    with open('books_export.json', 'r', encoding='utf-8') as f:
        books = json.load(f)

    print(f"[OK] Загружено {len(books)} книг из JSON")
    print()

    # Инициализируем Firebase
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred, {
                'projectId': 'nurbooks-a0eae'
            })

        db = firestore.client()
        print("[OK] Подключено к Firestore")
        print()
    except Exception as e:
        print(f"[ERR] Ошибка подключения: {e}")
        return

    # Загружаем книги
    success = 0
    failed = 0

    for i, book in enumerate(books, 1):
        book_id = str(book['id'])
        title = book['title'][:40]

        doc_data = {
            'id': book['id'],
            'title': book['title'],
            'author': book['author'],
            'category': book['category'] if book['category'] != 'NULL' else '',
            'year': book['year'],
            'description': book['description'],
            'cover': book['cover'],
            'pdf': book['pdf'],
            'fileSize': book['file_size'],
            'pages': book['pages'],
            'copyrightProtected': bool(book['copyright_protected']),
            'viewCount': book['view_count'],
            'downloadCount': book['download_count'],
            'createdAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        }

        try:
            doc_ref = db.collection('books').document(book_id)
            doc_ref.set(doc_data)
            safe_title = book['title'][:40].encode('ascii', 'replace').decode()
            print(f"  [{i}/{len(books)}] OK: {safe_title}... (ID: {book_id})")
            success += 1
        except Exception as e:
            safe_title = book['title'][:30].encode('ascii', 'replace').decode()
            print(f"  [{i}/{len(books)}] ERR: {safe_title}... ({e})")
            failed += 1

    print()
    print("=" * 60)
    print(f"Результат: {success} успешно, {failed} ошибок из {len(books)}")
    print("=" * 60)


if __name__ == "__main__":
    load_and_upload()
